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

## LUT composition (#22)

One builder validates settings, constructs a B/G/R grid (red changes fastest),
adds luminance-weighted shadow/highlight tint scaled by look intensity, applies
Rec.709-weighted saturation (style multiplier blended by intensity, then the
saturation control), contrast about encoded 0.5, and red/blue warmth. It clips
once and returns float32 SDR sRGB/Rec.709 RGB in 0..1. This is an artistic
operation on encoded SDR values, not a scene-linear/HDR color transform.
Default controls are 80/0/0/0; all four are required in API requests. Zero
intensity with the other controls zero is exact identity on the 1/32 grid;
other comparisons permit float32 rounding (absolute tolerance 1e-7).
The render and .cube paths both use this builder. Extraction quality remains
limited as documented in evaluation/README.md; the user authorized proceeding.

## Generation limits (#23)

Uploads are bounded to 15,728,640 bytes, with at most 1 MiB of multipart overhead,
and 24 million decoded pixels. JPEG/PNG/WebP signatures and decoded contents are
verified; malformed or incomplete multipart is rejected and all handles close on
failure. The analysis copy is orientation-correct and at most 1024 px. Generation
uses the conservative v2 neutral-anchor estimate evaluated under #18. The user
explicitly authorized continued engineering despite its documented NO-GO;
convincing photographic grade recovery and laptop qualification remain unproven.

## In-memory application (#27)

`uv run uvicorn app.main:app --port 8091` now defaults to isolated process-local
in-memory storage; accounts and sessions reset on restart. No migrations or DB
sessions are used in this mode. `create_app(users=MemoryUsers(), sessions=...)`
allows isolated test/application injection. The existing persistent implementation
is retained with `GRADEMATCH_STORAGE=orm` and its migration instructions above.
Bearer tokens are random opaque values; only SHA-256 digests are held by the
in-memory session repository. Registration returns only the contract's public user
and bearer envelope. Existing ORM regression tests explicitly select ORM mode.

Memory bearer sessions expire after seven days and are revoked individually by
logout. Session clocks and TTLs are injectable for deterministic expiry tests.
Missing, malformed, unknown, expired and revoked tokens return the same 401 auth
error; logout returns an empty 204. Logging out one session leaves other sessions
for the same or another account active. The client should clear its local token
even if logout reports 401, as required by the contract.
