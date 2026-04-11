from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Mapping


@dataclass
class User:
    """Сущность пользователя для мини-системы бронирования."""

    TABLE_NAME: ClassVar[str] = "users"

    email: str
    password_hash: str
    full_name: str
    id: int | None = None
    phone: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> User:
        return cls(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            phone=row.get("phone"),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_db_dict(self, *, include_id: bool = False) -> dict[str, Any]:
        """Поля для insert/update через PostgresDriver (ключи = имена колонок)."""
        data: dict[str, Any] = {
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "phone": self.phone,
            "is_active": self.is_active,
        }
        if include_id and self.id is not None:
            data["id"] = self.id
        return {k: v for k, v in data.items() if v is not None or k == "phone"}


CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {User.TABLE_NAME} (
    id            SERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    phone         TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
