# Task Manager (Desktop)

## Structure

- `app/main.py` entrypoint
- `app/ui/` UI layer (Qt widgets, dialogs, styles)
- `app/services/` use-cases and orchestration
- `app/domain/` entities, enums, filters
- `app/infra/` DB + repositories + logging
- `migrations/` Alembic migrations
- `tests/` pytest checks

## Features

- Kanban board + drag-and-drop across statuses
- Manual ordering inside status lists
- CSV import/export
- ICS export + optional auto-export
- Pomodoro timer
- Weekly reports

## Setup

1) Create `.env` from the example:

```
copy .env.example .env
```

2) Edit `.env` and set your database URL:

```
DATABASE_URL=postgresql+psycopg://task_user:your_password@localhost:5432/task_manager
```

3) Create a virtual environment and install dependencies:

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

4) Apply migrations:

```
python -m alembic upgrade head
```

5) Run the app:

```
python -m app.main
```

## Optional

- Auto-export ICS by setting `ICS_EXPORT_PATH` in `.env`.

## Tests

```
pytest
```
