from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Mapping


@dataclass
class Booking:
    """Сущность бронирования для системы ресторана."""

    TABLE_NAME: ClassVar[str] = "bookings"

    user_id: int                # ID пользователя, который сделал бронирование (внешний ключ)
    table_id: int               # ID стола, который забронирован (внешний ключ)
    booking_time: datetime      # Время бронирования (дата и время резерва)
    guests_count: int           # Количество гостей для бронирования
    id: int | None = None       # ID самого бронирования (PRIMARY KEY)
    special_request: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Booking:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            table_id=row["table_id"],
            booking_time=row["booking_time"],
            guests_count=row["guests_count"],
            special_request=row.get("special_request"),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_db_dict(self, *, include_id: bool = False) -> dict[str, Any]:
        """Поля для insert/update через PostgresDriver (ключи = имена колонок)."""
        data: dict[str, Any] = {
            "user_id": self.user_id,
            "table_id": self.table_id,
            "booking_time": self.booking_time,
            "guests_count": self.guests_count,
            "special_request": self.special_request,
            "is_active": self.is_active,
        }
        if include_id and self.id is not None:
            data["id"] = self.id
        return {k: v for k, v in data.items() if v is not None or k == "special_request"}


CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {Booking.TABLE_NAME} (
    id               SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    table_id         INT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    booking_time     TIMESTAMPTZ NOT NULL,
    guests_count     INT NOT NULL CHECK (guests_count > 0),
    special_request  TEXT,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""