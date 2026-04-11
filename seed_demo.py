"""Демо-данные: ≥3 пользователей, ≥3 столов, ≥2 бронирований (для проверки в PgAdmin)."""

from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

import backend
from models import Booking, Table, User


def main() -> None:
    backend.create_tables()

    users_data = [
        User(
            email="alice@demo.local",
            password_hash="demo_hash_1",
            full_name="Alice Demo",
        ),
        User(
            email="bob@demo.local",
            password_hash="demo_hash_2",
            full_name="Bob Demo",
        ),
        User(
            email="carol@demo.local",
            password_hash="demo_hash_3",
            full_name="Carol Demo",
        ),
    ]
    uids: list[int] = []
    for u in users_data:
        uids.append(backend.create_user(u))

    tables_data = [
        Table(name="Зал A / стол 1", capacity=4, location="У окна"),
        Table(name="Зал A / стол 2", capacity=2),
        Table(name="Веранда", capacity=6, location="Снаружи"),
    ]
    tids: list[int] = []
    for t in tables_data:
        tids.append(backend.create_table(t))

    t_first = tids[0]
    bookings_data = [
        Booking(
            user_id=uids[0],
            table_id=t_first,
            booking_time=datetime(2026, 4, 11, 10, 0, tzinfo=timezone.utc),
            guests_count=2,
        ),
        Booking(
            user_id=uids[1],
            table_id=t_first,
            booking_time=datetime(2026, 4, 11, 15, 0, tzinfo=timezone.utc),
            guests_count=3,
        ),
    ]
    bids: list[int] = []
    for b in bookings_data:
        bids.append(backend.create_booking(b))

    print("Пользователи (id):", uids)
    print("Столы (id):", tids)
    print("Бронирования (id):", bids)
    print(
        "Откройте в PgAdmin таблицы public.users, public.tables, public.bookings "
        "и убедитесь, что строки на месте."
    )


if __name__ == "__main__":
    main()
