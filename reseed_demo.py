# -*- coding: utf-8 -*-
"""Удаляет строки из users/tables/bookings и снова загружает демо-данные (UTF-8).

Используйте после правки кодировки в драйвере, если старые строки уже сохранены
«кракозябрами» — их автоматически не починить, только перезаписать.
"""

from dotenv import load_dotenv

load_dotenv()

from postgres_driver import PostgresSQLDriver


def main() -> None:
    with PostgresSQLDriver() as db:
        db.execute(
            "TRUNCATE bookings, tables, users RESTART IDENTITY CASCADE;",
        )
    import seed_demo

    seed_demo.main()
    print("Перезагрузка демо-данных завершена. Проверьте pgAdmin.")


if __name__ == "__main__":
    main()
