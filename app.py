"""Точка входа приложения (GUI): загрузка .env и запуск tkinter."""

from dotenv import load_dotenv

load_dotenv()

from gui import main

if __name__ == "__main__":
    main()
