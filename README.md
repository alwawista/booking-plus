# Бронирование столиков (PostgreSQL + Python)

Мини-приложение: пользователи, столы ресторана, бронирования с проверкой доступности слота и запретом пересечений активных броней на одном столе.

## Требования

- Python 3.10+
- Сервер PostgreSQL и учётная запись с правом создавать таблицы в выбранной базе

## Установка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка окружения

Скопируйте [`EnvExample`](EnvExample) или [`.env.example`](.env.example) в `.env` и укажите `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (пароль только в локальном `.env`, не коммитить).

Клиент к БД принудительно использует UTF-8 (`PGCLIENTENCODING`, параметры `psycopg2.connect`), чтобы кириллица корректно отображалась в pgAdmin.

## Запуск

```bash
python app.py
```

На вкладке **«База данных»** — **«Создать таблицы»**; далее пользователи, столы, бронирования. На вкладке **«Доступность»** — **«Проверить»** (проверка слота без записи в БД).

## Проверка в PgAdmin

Подключитесь к базе из `DB_NAME`, откройте **Schemas → public → Tables**: `users`, `tables`, `bookings`.

## Состав репозитория (по заданию)

| Файл | Назначение |
|------|------------|
| [`postgres_driver.py`](postgres_driver.py) | Подключение к PostgreSQL, DDL, CRUD-хелперы |
| [`backend.py`](backend.py) | Таблицы, CRUD, `check_table_availability` |
| [`models/`](models/) | Модели `User`, `Table`, `Booking` |
| [`app.py`](app.py) | GUI (tkinter) и точка входа |
| [`requirements.txt`](requirements.txt) | Зависимости |
| [`.env.example`](.env.example), [`EnvExample`](EnvExample) | Шаблон переменных без секретов (пароль только в `.env`) |
| [`README.md`](README.md) | Этот файл |

## Зависимости

- `psycopg2-binary` — драйвер PostgreSQL
- `python-dotenv` — загрузка переменных из `.env`
