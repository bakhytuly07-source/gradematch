# GradeMatch API

Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, SQLite. Контракт — `../openapi.yaml`.

Из корня проекта:

```sh
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8091
```

Документация: http://localhost:8091/docs. CORS разрешён для http://localhost:5173.
SQLite хранится в `backend/gradematch.db`, независимо от текущего каталога запуска.
Можно задать `DATABASE_URL` перед миграцией и запуском. Таблицы создаются миграциями;
приложение не меняет схему автоматически.

```sh
uv run pytest
uv run alembic check
```

## Данные и авторизация

`users` хранит нормализованный email и bcrypt-хеш предварительно хешированного SHA-256
пароля (поддерживаются пароли длиннее 72 байт). `access_tokens` хранит только SHA-256
хеши случайных bearer-токенов; срок действия — 7 дней, logout удаляет текущий токен.
`looks` принадлежит пользователю; чужие записи дают 404. Все даты — Unix milliseconds.
Параметры стиля и adjustments хранятся в JSON через ORM.

Исходные изображения не сохраняются. Multipart разбирается в памяти с ограничением
15 MiB на файл и 1 MiB на обрамление запроса; анализ использует копию до 1024 px.
Проверяются сигнатура и декодированный формат JPEG/PNG/WebP. При сохранении библиотека
принимает пустую строку или JPEG data URL, пересоздаёт JPEG миниатюру до 256 px и удаляет
метаданные. Гости не создают записей в БД.

Алгоритм извлечения стиля — базовая детерминированная оценка баланса теней/светов
и насыщенности; это приближение цветового стиля, а не восстановление исходного грейда.
LUT — 33³, нормализованный SDR sRGB/Rec.709. Рендер и экспорт используют одну функцию;
9 значащих цифр в `.cube` обеспечивают точный round-trip float32.

## Фронтенд

В `frontend/src/services/api.ts` реализован `GradeMatchService`. Для подключения:

```sh
cd ../frontend
VITE_API_URL=http://localhost:8091 npm run dev -- --port 5173
```

Без `VITE_API_URL` остаётся MockService. Адаптер хранит токен в памяти до обновления
страницы, отправляет Authorization, преобразует JSON-массив LUT в Float32Array,
ответы Look: `style_params → styleParams`, `thumbnail_url → thumbnail`,
`is_favorite → favorite`, `created_at → createdAt`. `updated_at` есть в API, но
отсутствует в текущем интерфейсе UI. **Запросы SaveLookInput, LutSettings и вложенный
StyleParams сохраняют camelCase**, как требует контракт. getMe преобразует 401 в null.
Нужен настоящий File/Blob для generateLook; объект только с метаданными не загружается.

## Dependency approval and startup smoke test (#17)

On 2026-10-19 the user approved FastAPI, Uvicorn, NumPy, Pillow,
opencv-python-headless, bcrypt, python-multipart, pytest and HTTPX, including
uv-locked transitive dependencies. Existing SQLAlchemy/Alembic and contract-test
dependencies are retained from main; no additional packages are introduced here.
The supported engineering runtime is Python 3.12. `uv sync --locked` installs the
reproducible environment. `uv run pytest tests/test_startup.py` exercises ASGI
startup and shutdown without database access. The existing product routes and ORM
implementation from main are retained; the smoke test does not require migrations.
