# URL Shortener (Django)

A minimal URL shortener built with Django and Django REST Framework.

## What this project does

- Accepts a long URL
- Generates a short code
- Redirects from short code to the original URL
- Provides API documentation with Swagger/OpenAPI
- Runs with Docker + Postgres

## Tech stack

- Python 3.10
- Django 5
- Django REST Framework
- drf-spectacular (OpenAPI/Swagger)
- PostgreSQL
- Docker and Docker Compose
- Poetry

## Project structure

- apps/core: Base app
- apps/shortener: URL model and short-code logic
- apps/api: API layer
- config: Django settings and URL routing

## Environment variables

Copy .env.example to .env and update values if needed.

Required values:

- SECRET_KEY
- DEBUG
- DJANGO_SETTINGS_MODULE
- DATABASE_URL
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

Example values are already provided in .env.example.

## Run with Docker (recommended)

1. Build and start services:

```bash
docker compose up --build
```

2. App URL:

- http://localhost:8000

3. Stop services:

```bash
docker compose down
```

## Run locally (without Docker)

1. Install dependencies:

```bash
poetry install
```

2. Create your .env file from .env.example.

3. Run migrations:

```bash
poetry run python manage.py migrate
```

4. Start server:

```bash
poetry run python manage.py runserver
```

## API endpoints

- POST /api/urls/
  - Create a short URL
  - Body:

```json
{
  "original_url": "https://example.com/some/long/path"
}
```

- GET /<short_code>/
  - Redirect to the original URL (HTTP 302)

- GET /api/schema/
  - OpenAPI schema

- GET /api/docs/
  - Swagger UI

## Notes

- Short codes are generated as random 6-character alphanumeric strings.
- If the same original URL is submitted again, the existing short code is returned.
