"""Точка входа приложения (GUI): загрузка .env и запуск tkinter."""

import os

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

from dotenv import load_dotenv

load_dotenv()

from gui import main

if __name__ == "__main__":
    main()
