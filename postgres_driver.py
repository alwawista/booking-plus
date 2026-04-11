import os
from contextlib import contextmanager
from urllib.parse import quote_plus
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Type, get_args, get_type_hints
from uuid import UUID

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor


class PostgresDriver:
    def __init__(self, autoload_env: bool = True) -> None:
        self._conn: psycopg2.extensions.connection | None = None

        if autoload_env:
            self._load_env_with_fallback()

        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME", "postgres")
        self.db_user = os.getenv("DB_USER", "postgres")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_client_encoding = os.getenv("DB_CLIENT_ENCODING", "").strip()
        if not self.db_password:
            raise RuntimeError(
                "DB_PASSWORD is missing. Set it in your .env file."
            )

    def _connect_dsn(self) -> str:
        """URI with percent-encoded credentials — avoids libpq/psycopg2 decode issues on Windows."""
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        db = quote_plus(self.db_name)
        port = str(self.db_port).strip()
        return (
            f"postgresql://{user}:{password}@{self.db_host}:{port}/{db}"
            f"?connect_timeout=5"
        )

    def _configure_client_encoding(self, conn: psycopg2.extensions.connection) -> None:
        """Apply DB_CLIENT_ENCODING after connect (e.g. WIN1251 for localized server messages)."""
        if not self.db_client_encoding:
            return
        with conn.cursor() as cur:
            cur.execute("SET client_encoding TO %s", (self.db_client_encoding,))

    def __enter__(self) -> PostgresDriver:
        self._conn = psycopg2.connect(self._connect_dsn())
        self._configure_client_encoding(self._conn)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._conn is not None:
            if exc_type is not None:
                self._conn.rollback()
            self._conn.close()
            self._conn = None

    @staticmethod
    def _load_env_with_fallback() -> None:
        for encoding in ("utf-8", "utf-8-sig", "cp1251"):
            try:
                load_dotenv(encoding=encoding)
                return
            except UnicodeDecodeError:
                continue
        load_dotenv()

    @contextmanager
    def _connection(self):
        if self._conn is not None:
            yield self._conn
        else:
            with psycopg2.connect(self._connect_dsn()) as conn:
                self._configure_client_encoding(conn)
                yield conn

    def _commit_if_managed(self, conn: psycopg2.extensions.connection) -> None:
        if self._conn is not None:
            conn.commit()

    @staticmethod
    def _unwrap_optional(py_type: Any) -> Any:
        args = get_args(py_type)
        if args and type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return non_none[0]
        return py_type

    @staticmethod
    def _python_type_to_postgres(py_type: Any) -> str:
        t = PostgresDriver._unwrap_optional(py_type)
        if t is str:
            return "TEXT"
        if t is int:
            return "INTEGER"
        if t is bool:
            return "BOOLEAN"
        if t is float:
            return "DOUBLE PRECISION"
        if t is Decimal:
            return "NUMERIC"
        if t is datetime:
            return "TIMESTAMPTZ"
        if t is date:
            return "DATE"
        if t is bytes:
            return "BYTEA"
        if t is UUID:
            return "UUID"
        raise TypeError(f"Unsupported type for auto DDL: {py_type!r}")

    @staticmethod
    def _field_allows_null_with_type(_field: Any, ftype: Any) -> bool:
        args = get_args(ftype)
        return bool(args) and type(None) in args

    @staticmethod
    def _generate_create_table_sql(model_cls: Type[Any]) -> str:
        if not is_dataclass(model_cls):
            raise TypeError(
                f"_generate_create_table_sql expects a dataclass, got {model_cls!r}"
            )
        table_name = getattr(model_cls, "TABLE_NAME", None)
        if not table_name:
            raise ValueError(f"Model {model_cls.__name__} must define TABLE_NAME.")

        hints = get_type_hints(model_cls)
        ordered = sorted(
            fields(model_cls),
            key=lambda f: (0 if f.name == "id" else 1, f.name),
        )
        col_lines: list[str] = []
        for field in ordered:
            ftype = hints.get(field.name, field.type)
            if field.name == "id":
                inner = PostgresDriver._unwrap_optional(ftype)
                if inner is int:
                    col_lines.append("id SERIAL PRIMARY KEY")
                    continue
            pg_type = PostgresDriver._python_type_to_postgres(ftype)
            null_sql = (
                "NULL"
                if PostgresDriver._field_allows_null_with_type(field, ftype)
                else "NOT NULL"
            )
            col_lines.append(f"{field.name} {pg_type} {null_sql}")

        cols_sql = ",\n    ".join(col_lines)
        return (
            f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            f"    {cols_sql}\n"
            f");"
        )

    def _check_table_exists(self, table_name: str, schema: str = "public") -> bool:
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            );
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (schema, table_name))
                row = cur.fetchone()
                return bool(row[0])

    def create_table_from_model(self, model_cls: Type[Any]) -> bool:
        table_name = getattr(model_cls, "TABLE_NAME", None)
        if not table_name:
            raise ValueError(f"Model {model_cls.__name__} must define TABLE_NAME.")

        if self._check_table_exists(table_name):
            return False

        create_sql = getattr(model_cls, "CREATE_TABLE_SQL", None)
        if create_sql and str(create_sql).strip():
            sql_str = str(create_sql).strip()
        else:
            sql_str = self._generate_create_table_sql(model_cls)

        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_str)
            self._commit_if_managed(conn)
        return True

    @staticmethod
    def _build_columns(columns: list[str] | None) -> sql.SQL:
        if not columns:
            return sql.SQL("*")
        return sql.SQL(", ").join(sql.Identifier(col) for col in columns)

    @staticmethod
    def _build_where(filters: dict[str, Any] | None) -> tuple[sql.SQL, list[Any]]:
        if not filters:
            return sql.SQL(""), []

        conditions = []
        values = []
        for key, value in filters.items():
            conditions.append(
                sql.SQL("{} = %s").format(sql.Identifier(key))
            )
            values.append(value)

        return (
            sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions),
            values,
        )

    def test_connection(self) -> str:
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                return cur.fetchone()[0]

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        fetch: str | None = None,
    ) -> Any:
        with self._connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch == "one":
                    result = cur.fetchone()
                elif fetch == "all":
                    result = cur.fetchall()
                else:
                    result = cur.rowcount
            self._commit_if_managed(conn)
            return result

    def create(
        self,
        table: str,
        data: dict[str, Any],
        returning: str | None = "id",
    ) -> Any:
        if not data:
            raise ValueError("data must not be empty for create().")

        columns = list(data.keys())
        values = list(data.values())
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)

        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            placeholders,
        )

        if returning:
            query += sql.SQL(" RETURNING {}").format(sql.Identifier(returning))

        with self._connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, values)
                if returning:
                    row = cur.fetchone()
                    out = row[returning] if row else None
                else:
                    out = None
            self._commit_if_managed(conn)
            return out

    def read_one(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
    ) -> dict[str, Any] | None:
        cols_sql = self._build_columns(columns)
        where_sql, where_values = self._build_where(filters)

        query = (
            sql.SQL("SELECT {} FROM {}").format(
                cols_sql, sql.Identifier(table)
            )
            + where_sql
            + sql.SQL(" LIMIT 1")
        )

        with self._connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, where_values)
                return cur.fetchone()

    def read_many(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        cols_sql = self._build_columns(columns)
        where_sql, where_values = self._build_where(filters)

        query = (
            sql.SQL("SELECT {} FROM {}").format(
                cols_sql, sql.Identifier(table)
            )
            + where_sql
        )

        params = list(where_values)
        if limit is not None:
            query += sql.SQL(" LIMIT %s")
            params.append(limit)
        if offset is not None:
            query += sql.SQL(" OFFSET %s")
            params.append(offset)

        with self._connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any] | None = None,
    ) -> int:
        if not data:
            raise ValueError("data must not be empty for update().")

        set_parts = []
        values = []
        for key, value in data.items():
            set_parts.append(
                sql.SQL("{} = %s").format(sql.Identifier(key))
            )
            values.append(value)

        where_sql, where_values = self._build_where(filters)
        query = (
            sql.SQL("UPDATE {} SET ").format(sql.Identifier(table))
            + sql.SQL(", ").join(set_parts)
            + where_sql
        )

        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values + where_values)
                rc = cur.rowcount
            self._commit_if_managed(conn)
            return rc

    def delete(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
    ) -> int:
        where_sql, where_values = self._build_where(filters)
        query = sql.SQL("DELETE FROM {}").format(sql.Identifier(table)) + where_sql

        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, where_values)
                rc = cur.rowcount
            self._commit_if_managed(conn)
            return rc


PostgresSQLDriver = PostgresDriver
