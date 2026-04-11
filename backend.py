"""Бэкенд: создание таблиц и CRUD по моделям User, Table, Booking."""

from datetime import datetime, timedelta, timezone

from postgres_driver import PostgresSQLDriver

from models import Booking, Table, User

DEFAULT_BOOKING_SLOT = timedelta(hours=2)


def create_tables() -> None:
    """DDL: создаёт таблицы в БД (users, tables, bookings), если их ещё нет."""
    with PostgresSQLDriver() as db:
        db.create_table_from_model(User)
        db.create_table_from_model(Table)
        db.create_table_from_model(Booking)


def check_table_availability(
    table_id: int,
    booking_time: datetime,
    slot_duration: timedelta = DEFAULT_BOOKING_SLOT,
    exclude_booking_id: int | None = None,
) -> bool:
    """
    True, если стол свободен в полуинтервале [booking_time, booking_time + slot_duration).
    Учитываются только активные брони (is_active = TRUE).
    exclude_booking_id — исключить бронь при редактировании.
    """
    end_time = booking_time + slot_duration
    with PostgresSQLDriver() as db:
        if exclude_booking_id is None:
            sql = """
                SELECT NOT EXISTS (
                    SELECT 1 FROM bookings
                    WHERE table_id = %s
                      AND is_active = TRUE
                      AND booking_time < %s
                      AND %s < booking_time + %s * INTERVAL '1 second'
                ) AS ok
            """
            total_seconds = int(slot_duration.total_seconds())
            row = db.execute(
                sql,
                (table_id, end_time, booking_time, total_seconds),
                fetch="one",
            )
        else:
            sql = """
                SELECT NOT EXISTS (
                    SELECT 1 FROM bookings
                    WHERE table_id = %s
                      AND is_active = TRUE
                      AND id <> %s
                      AND booking_time < %s
                      AND %s < booking_time + %s * INTERVAL '1 second'
                ) AS ok
            """
            total_seconds = int(slot_duration.total_seconds())
            row = db.execute(
                sql,
                (table_id, exclude_booking_id, end_time, booking_time, total_seconds),
                fetch="one",
            )
    if row is None:
        return True
    return bool(row["ok"])


def _ensure_booking_slot_free(
    table_id: int,
    booking_time: datetime,
    *,
    exclude_booking_id: int | None = None,
    slot_duration: timedelta = DEFAULT_BOOKING_SLOT,
) -> None:
    if not check_table_availability(
        table_id,
        booking_time,
        slot_duration=slot_duration,
        exclude_booking_id=exclude_booking_id,
    ):
        raise ValueError(
            "Стол занят: пересечение с существующей активной бронью в этом временном слоте."
        )


# --- User ---


def create_user(user: User) -> int:
    """Вставляет пользователя; возвращает id."""
    data = user.to_db_dict()
    data.pop("id", None)
    with PostgresSQLDriver() as db:
        new_id = db.create(User.TABLE_NAME, data, returning="id")
    if new_id is None:
        raise RuntimeError("INSERT users did not return id.")
    return int(new_id)


def get_all_users() -> list[User]:
    """Все пользователи по возрастанию id."""
    with PostgresSQLDriver() as db:
        rows = db.execute(
            f"SELECT * FROM {User.TABLE_NAME} ORDER BY id",
            fetch="all",
        )
    if not rows:
        return []
    return [User.from_row(r) for r in rows]


def get_user_by_id(user_id: int) -> User | None:
    with PostgresSQLDriver() as db:
        row = db.read_one(User.TABLE_NAME, {"id": user_id})
    return User.from_row(row) if row else None


def update_user(user: User) -> int:
    """Обновляет пользователя по user.id; возвращает число затронутых строк."""
    if user.id is None:
        raise ValueError("update_user: user.id is required.")
    now = datetime.now(timezone.utc)
    data = user.to_db_dict()
    data.pop("id", None)
    data["updated_at"] = now
    with PostgresSQLDriver() as db:
        return db.update(User.TABLE_NAME, data, {"id": user.id})


def delete_user(user_id: int) -> int:
    with PostgresSQLDriver() as db:
        return db.delete(User.TABLE_NAME, {"id": user_id})


# --- Table (стол ресторана; таблица БД `tables`) ---


def create_table(table: Table) -> int:
    """Вставляет запись о столе (не путать с create_tables — DDL)."""
    data = table.to_db_dict()
    data.pop("id", None)
    with PostgresSQLDriver() as db:
        new_id = db.create(Table.TABLE_NAME, data, returning="id")
    if new_id is None:
        raise RuntimeError("INSERT tables did not return id.")
    return int(new_id)


def get_all_tables() -> list[Table]:
    with PostgresSQLDriver() as db:
        rows = db.execute(
            f"SELECT * FROM {Table.TABLE_NAME} ORDER BY id",
            fetch="all",
        )
    if not rows:
        return []
    return [Table.from_row(r) for r in rows]


def get_table_by_id(table_id: int) -> Table | None:
    with PostgresSQLDriver() as db:
        row = db.read_one(Table.TABLE_NAME, {"id": table_id})
    return Table.from_row(row) if row else None


def update_table(table: Table) -> int:
    if table.id is None:
        raise ValueError("update_table: table.id is required.")
    now = datetime.now(timezone.utc)
    data = table.to_db_dict()
    data.pop("id", None)
    data["updated_at"] = now
    with PostgresSQLDriver() as db:
        return db.update(Table.TABLE_NAME, data, {"id": table.id})


def delete_table(table_id: int) -> int:
    with PostgresSQLDriver() as db:
        return db.delete(Table.TABLE_NAME, {"id": table_id})


# --- Booking ---


def create_booking(booking: Booking) -> int:
    if booking.is_active:
        _ensure_booking_slot_free(booking.table_id, booking.booking_time)
    data = booking.to_db_dict()
    data.pop("id", None)
    with PostgresSQLDriver() as db:
        new_id = db.create(Booking.TABLE_NAME, data, returning="id")
    if new_id is None:
        raise RuntimeError("INSERT bookings did not return id.")
    return int(new_id)


def get_all_bookings() -> list[Booking]:
    with PostgresSQLDriver() as db:
        rows = db.execute(
            f"SELECT * FROM {Booking.TABLE_NAME} ORDER BY id",
            fetch="all",
        )
    if not rows:
        return []
    return [Booking.from_row(r) for r in rows]


def get_booking_by_id(booking_id: int) -> Booking | None:
    with PostgresSQLDriver() as db:
        row = db.read_one(Booking.TABLE_NAME, {"id": booking_id})
    return Booking.from_row(row) if row else None


def update_booking(booking: Booking) -> int:
    if booking.id is None:
        raise ValueError("update_booking: booking.id is required.")
    if booking.is_active:
        _ensure_booking_slot_free(
            booking.table_id,
            booking.booking_time,
            exclude_booking_id=booking.id,
        )
    now = datetime.now(timezone.utc)
    data = booking.to_db_dict()
    data.pop("id", None)
    data["updated_at"] = now
    with PostgresSQLDriver() as db:
        return db.update(Booking.TABLE_NAME, data, {"id": booking.id})


def delete_booking(booking_id: int) -> int:
    with PostgresSQLDriver() as db:
        return db.delete(Booking.TABLE_NAME, {"id": booking_id})


if __name__ == "__main__":
    create_tables()
