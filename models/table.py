from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Mapping


@dataclass
class Table:
    """Сущность стола для системы бронирования ресторана."""

    TABLE_NAME: ClassVar[str] = "tables"

    name: str
    capacity: int
    id: int | None = None
    location: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Table:
        return cls(
            id=row["id"],
            name=row["name"],
            capacity=row["capacity"],
            location=row.get("location"),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_db_dict(self, *, include_id: bool = False) -> dict[str, Any]:
        """Поля для insert/update через PostgresDriver (ключи = имена колонок)."""
        data: dict[str, Any] = {
            "name": self.name,
            "capacity": self.capacity,
            "location": self.location,
            "is_active": self.is_active,
        }
        if include_id and self.id is not None:
            data["id"] = self.id
        return {k: v for k, v in data.items() if v is not None or k == "location"}


CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {Table.TABLE_NAME} (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    capacity   INT NOT NULL CHECK (capacity > 0),
    location   TEXT,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""