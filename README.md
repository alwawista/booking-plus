# Бронирование столиков (PostgreSQL + Python)

Мини-приложение: пользователи, столы ресторана, бронирования с проверкой доступности слота и запретом пересечений активных броней на одном столе.

## Требования

- Python 3.10+
- Сервер PostgreSQL и учётная запись с правом создавать таблицы в выбранной базе

## Установка

```bash
cd VPc07
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка окружения

Скопируйте [`.env.example`](.env.example) в `.env` и укажите параметры подключения:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — обязательно (пароль в `.env`, не коммитить).

Подключение к PostgreSQL выставляет **UTF-8**: переменная окружения `PGCLIENTENCODING=UTF8` до загрузки libpq, параметры `psycopg2.connect(..., options='-c client_encoding=UTF8')` и `connection.set_client_encoding('UTF8')`. На Windows без этого кириллица из Python часто превращается в строки вида `РЈ РѕРєРЅР°` вместо «У окна».

**Уже испорченные строки** автоматически не восстанавливаются (это другой набор символов Unicode, не «Latin-1 → UTF-8»). Очистите таблицы и вставьте данные заново:

```bash
python reseed_demo.py
```

Скрипт выполняет `TRUNCATE ... CASCADE` по `users`, `tables`, `bookings` и снова вызывает логику `seed_demo.py`.

В коде используется `load_dotenv()` (см. [`app.py`](app.py), [`postgres_driver.py`](postgres_driver.py)).

## Запуск GUI

```bash
python app.py
```

Эквивалентно:

```bash
python main.py
```

Рекомендуемый порядок: на вкладке **«База данных»** нажать **«Создать таблицы»**, затем работать с пользователями, столами и бронированиями. На вкладке **«Доступность»** — кнопка **«Проверить»** (проверка слота без записи в БД).

## Демо-данные (базовый уровень сдачи)

После настройки `.env`:

```bash
python seed_demo.py
```

Скрипт создаёт таблицы (если их ещё нет), не менее трёх пользователей, трёх столов и двух бронирований с непересекающимися интервалами на одном столе. В консоль выводятся идентификаторы.

Повторный запуск может завершиться ошибкой уникальности (`email` / `name`) — удалите тестовые строки в БД или смените значения в `seed_demo.py`.

## Проверка в PgAdmin

1. Подключитесь к той же базе, что указана в `DB_NAME`.
2. Откройте **Schemas → public → Tables** и просмотрите `users`, `tables`, `bookings` (например **View/Edit Data → All Rows**).

## Состав репозитория (для ссылки на GitHub)

Минимальный набор по заданию:

| Файл / папка | Назначение |
|--------------|------------|
| [`postgres_driver.py`](postgres_driver.py) | Драйвер PostgreSQL, DDL, CRUD-хелперы |
| [`backend.py`](backend.py) | Таблицы, CRUD, `check_table_availability`, запрет пересечений броней |
| [`models/`](models/) (`__init__.py`, `user.py`, `table.py`, `booking.py`) | Модели данных |
| [`app.py`](app.py) | Точка входа (средний уровень: GUI через `load_dotenv`) |
| [`requirements.txt`](requirements.txt) | Зависимости (`pip install -r requirements.txt`) |
| [`.env.example`](.env.example) | Шаблон переменных окружения **без секретов** (пароль подставляете только в локальный `.env`) |
| [`README.md`](README.md) | Этот файл: установка и команды запуска |

Дополнительно в проекте: [`gui.py`](gui.py) (интерфейс tkinter), [`main.py`](main.py) (альтернативный запуск), [`seed_demo.py`](seed_demo.py) (демо-данные).

Перед пушем на GitHub убедитесь, что файл `.env` с паролем **не** попал в репозиторий (в корне есть [`.gitignore`](.gitignore)).

## Зависимости

- `psycopg2-binary` — драйвер PostgreSQL
- `python-dotenv` — загрузка переменных из `.env`
