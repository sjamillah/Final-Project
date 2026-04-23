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

- POST /api/v1/urls/
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

---

# Module 6: ORM & Data Access Layer

## Goal

Expand the data model to support users, relationships, and deep analytics. Make the application "smart" by adding user ownership, tagging, and analytics tracking.

## What This Module Adds

After establishing the core URL shortener, Module 6 focuses on:
- **User Management**: Track who created each short link
- **Tagging & Categorization**: Organize links with meaningful tags
- **Analytics Tracking**: Log every visit with detailed metadata
- **Query Optimization**: Fetch data efficiently without N+1 problems

## Database Schema (Module 6)

### User Model
**Purpose**: Extended Django user with premium tier support.

**Fields**:
- `email` (EmailField, Unique, Required): User's email address
- `is_premium` (BooleanField, Default: False): Premium status indicator
- `tier` (CharField, Choices: 'free', 'premium', 'admin'): User tier level
- Inherits from Django's `AbstractUser`

### URL Model (Enhanced)
**Purpose**: Stores mapping between short codes and original long URLs with ownership and metadata.

**Fields**:
- `original_url` (URLField, Max 2048 chars): The long URL to redirect to
- `short_code` (CharField, Unique, Indexed, Max 10): 6-char alphanumeric identifier
- `custom_alias` (CharField, Nullable, Unique): Vanity URL (premium feature)
- `owner` (ForeignKey to User, ON DELETE CASCADE): URL creator
- `is_active` (BooleanField, Default: True): Soft delete flag
- `expires_at` (DateTimeField, Nullable): Expiration timestamp
- `title` (CharField, Nullable): User-defined title
- `description` (CharField, Nullable): User-defined description
- `favicon` (CharField, Nullable): URL icon/preview
- `click_count` (PositiveIntegerField, Default: 0): Denormalized click counter
- `created_at` (DateTimeField, Auto Now Add): Creation timestamp
- `tags` (ManyToManyField to Tag): Categorization

### Click Model (Analytics)
**Purpose**: Logs every visit to a short link for analytics.

**Fields**:
- `url` (ForeignKey to URL, ON DELETE CASCADE): The short link clicked
- `clicked_at` (DateTimeField, Auto Now Add): When the click occurred
- `ip_address` (GenericIPAddressField, Nullable): Visitor's IP
- `city` (CharField, Nullable): Geographic location (city)
- `country` (CharField, Nullable): Geographic location (country)
- `user_agent` (TextField, Nullable): Browser/OS info
- `referrer` (URLField, Nullable, Max 2048): Source of the click

### Tag Model
**Purpose**: Categorization system for URLs.

**Fields**:
- `name` (CharField, Unique, Max 50): Tag name (e.g., "Marketing", "Social")
- `urls` (ManyToManyField to URL): Related URLs

## Key Features

### Custom Managers
- `active_urls()`: Returns only active, non-expired URLs
- `expired_urls()`: Returns only expired URLs
- `popular_urls(threshold=100)`: Returns URLs with click_count above threshold

### Query Optimization
- **select_related()**: Prevents N+1 queries for ForeignKey relationships (User ownership)
- **prefetch_related()**: Prevents N+1 queries for ManyToMany relationships (Tags)
- **Database indexes**: On `short_code` for fast lookups and `created_at` for filtering
- **Aggregation**: Use annotate() for complex stats (e.g., clicks per country)

### Example Optimized Query
```python
# Efficiently fetch URLs with owner and tags
urls = URL.objects.select_related('owner').prefetch_related('tags').all()
```

### Analytics
- Every click is logged with geographic and referrer data
- Click count is denormalized for fast read access
- Soft deletes preserve analytics history via `is_active` flag

## Testing Module 6

Run all tests:
```bash
poetry run pytest -q
```

Test coverage includes:
- User model creation and tier assignment
- URL ownership and cascade delete behavior
- Click logging and timestamp accuracy
- Tag relationships
- Custom manager methods (active, expired, popular)
- Query optimization verification (no N+1 problems)

## Performance Metrics

- Short code lookup: O(1) with database index
- URL with owner fetch: 2 queries (URL + User)
- URL with tags: 2 queries (URL + tags via prefetch)
- Click logging: Immediate write, minimal overhead
- Analytics queries: Direct database aggregation (no Python loops)
