# URL Shortener API (Django 5 + PostgreSQL)

A production-grade URL shortening service with JWT authentication, user tiers, analytics, URL preview metadata, and API documentation.

## Table of Contents
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Features by Module](#features-by-module)
- [Module 8 Technical Details](#module-8-technical-details)
- [Module 9 Technical Details](#module-9-technical-details)
- [Database Schema](#database-schema)
- [Development](#development)
- [Testing](#testing)

## Tech Stack

- **Backend**: Python 3.10, Django 5.x, Django REST Framework
- **Database**: PostgreSQL 15
- **Caching**: Redis 7 (cache-aside pattern for redirects)
- **Async Tasks**: Celery 5 + Celery Beat (click tracking, URL cleanup, URL preview sync)
- **Authentication**: JWT via `djangorestframework-simplejwt`
- **API Docs**: drf-spectacular (OpenAPI 3.0 + Swagger UI)
- **Admin Interface**: Django Admin with custom base classes
- **Logging**: JSON structured logging for observability
- **Containerization**: Docker & Docker Compose (API, worker, beat, preview microservice)
- **Dependency Management**: Poetry
- **Testing**: pytest & pytest-django with async task fixtures
- **Code Quality**: Black, Ruff, pre-commit

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- OR Python 3.10+, Poetry, PostgreSQL running locally

### Run with Docker (Recommended)

1. **Clone and setup**:
```bash
git clone <repo-url>
cd Final-Project
cp .env.example .env
```

2. **Build and start services**:
```bash
docker compose up --build
```

This starts:
- `web`: Django API (port 8000)
- `db`: PostgreSQL (port 5434)
- `redis`: Redis cache (port 6380)
- `celery`: Celery worker for async tasks
- `celery-beat`: Celery Beat scheduler for nightly cleanup
- `preview_service`: URL metadata microservice (port 8001)

3. **Access the application**:
- API: http://localhost:8000/api/v1/
- Swagger UI (API Docs): http://localhost:8000/api/docs/
- Schema (OpenAPI JSON): http://localhost:8000/api/schema/
- Health Check: http://localhost:8000/api/v1/health/
- Django Admin: http://localhost:8000/admin/ (staff users)
- Preview Service Health: http://localhost:8001/health/

4. **View logs**:
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f celery
docker compose logs -f redis
```

5. **Stop services**:
```bash
docker compose down
```

### Run Locally (Without Docker)

1. **Install dependencies**:
```bash
poetry install
```

2. **Setup environment**:
```bash
cp .env.example .env
# Edit .env with your local PostgreSQL credentials
```

3. **Run migrations**:
```bash
poetry run python manage.py migrate
```

4. **Create a superuser (optional)**:
```bash
poetry run python manage.py createsuperuser
```

5. **Start development server**:
```bash
poetry run python manage.py runserver
```

**For Module 8 (Optional - Celery + Redis):**

If you want to test async tasks and caching locally:

6a. **Start Redis** (separate terminal):
```bash
# Using Docker just for Redis
docker run -it -p 6379:6379 redis:7-alpine

# Or if Redis installed locally
redis-server
```

6b. **Start Celery worker** (separate terminal):
```bash
poetry run celery -A config worker -l info
```

6c. **Start Celery Beat** (separate terminal):
```bash
poetry run celery -A config beat -l info
```

7. **Run tests**:
```bash
poetry run pytest -v
```

**Note**: Tests don't require Redis/Celery running - fixtures provide in-memory cache and eager task execution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client (Web/Mobile)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP/HTTPS
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Django REST API (Port 8000)                │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Authentication Layer (JWT)            │   │
│  │  • RegisterView, LoginView, LogoutView          │   │
│  │  • TokenRefreshView (simplejwt)                 │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         URL Management Endpoints (/v1/)          │   │
│  │  • URLListCreateView (GET/POST)                 │   │
│  │  • URLDetailView (GET/PUT/PATCH/DELETE)        │   │
│  │  • URLRedirectView (GET - public)               │   │
│  │  • URLAnalyticsView (GET - premium only)        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Domain Layer (apps/users +             │   │
│  │                apps/shortener)                  │   │
│  │  • users/services.py, selectors.py              │   │
│  │  • shortener/services.py (write operations)     │   │
│  │  • shortener/selectors.py (read operations)     │   │
│  │  • shortener/analytics.py (aggregations)        │   │
│  │  • shortener/cache.py (Redis cache)             │   │
│  │  • shortener/tasks.py (Celery async tasks)      │   │
│  │  • shortener/exceptions.py (domain errors)      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │             API Layer (apps/api/v1)             │   │
│  │  • views.py: HTTP orchestration                 │   │
│  │  • serializers.py: request/response validation  │   │
│  │  • permissions.py: DRF permission classes       │   │
│  │  • apps/api/throttles.py: DRF throttle classes  │   │
│  │  • health/views.py: Service monitoring          │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │        Data Access Layer (ORM + Indexes)         │   │
│  │  • models.py: User, URL, Click, Tag             │   │
│  │  • managers.py: QuerySet helpers                │   │
│  │  • migrations: Schema versioning                │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │      Logging & Monitoring (apps/core)            │   │
│  │  • logging.py: JSON structured logging          │   │
│  │  • admin.py: Django admin interface             │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────┘
               │
      ┌────────┼────────┐
      │        │        │
      ▼        ▼        ▼
  ┌────────┐ ┌───────┐ ┌──────────────┐
  │Postgres│ │ Redis │ │ Celery Tasks │
  │        │ │       │ │              │
  │Database│ │ Cache │ │ • Click      │
  │        │ │       │ │ • Cleanup    │
  └────────┘ └───────┘ └──────────────┘
                          │
                          ▼
                    ┌──────────────┐
                    │ Celery Beat  │
                    │ Scheduler    │
                    └──────────────┘
```

---

## API Endpoints

### Base URL
```
http://localhost:8000/api/v1/
```

### Authentication Endpoints

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|-----------|
| POST | `/auth/register/` | Register new user | None | - |
| POST | `/auth/login/` | Login & get JWT tokens | None | 5/min |
| POST | `/auth/refresh/` | Refresh access token | Refresh token | - |
| POST | `/auth/logout/` | Logout (blacklist token) | Bearer token | - |

**Request/Response Examples**:

**Register**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123"
  }'
```

Response (201):
```json
{
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "is_premium": false,
    "tier": "free"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Login**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123"
  }'
```

---

### URL Management Endpoints

| Method | Endpoint | Description | Auth | Permission |
|--------|----------|-------------|------|-----------|
| GET | `/urls/` | List user's URLs | Required | Authenticated |
| POST | `/urls/` | Create short URL | Required | Authenticated, Free tier limit: 10 URLs |
| GET | `/urls/{short_code}/` | Get URL details | Required | Owner or ReadOnly |
| PUT | `/urls/{short_code}/` | Full URL update | Required | Owner only |
| PATCH | `/urls/{short_code}/` | Partial URL update | Required | Owner only |
| DELETE | `/urls/{short_code}/` | Soft delete URL | Required | Owner only |
| GET | `/analytics/{short_code}/` | Get analytics | Required | Premium/Admin only |

**Create URL**:
```bash
curl -X POST http://localhost:8000/api/v1/urls/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com/very/long/path"
  }'
```

Response (201):
```json
{
  "id": 1,
  "original_url": "https://example.com/very/long/path",
  "short_code": "abc123",
  "custom_alias": null,
  "short_url": "http://localhost:8000/abc123/",
  "title": null,
  "click_count": 0,
  "is_active": true,
  "expires_at": null,
  "tags": [],
  "owner_username": "john",
  "created_at": "2026-04-30T12:00:00Z"
}
```

**Create with Optional Fields** (Premium feature):
```bash
curl -X POST http://localhost:8000/api/v1/urls/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://docs.example.com",
    "custom_alias": "docs",
    "title": "Documentation",
    "expires_at": "2026-12-31T23:59:59Z",
    "tags": ["documentation", "reference"]
  }'
```

**Get Analytics** (Premium only):
```bash
curl -X GET http://localhost:8000/api/v1/urls/abc123/analytics/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response (200):
```json
{
  "short_code": "abc123",
  "total_clicks": 42,
  "last_clicked": "2026-04-30T15:30:00Z",
  "clicks_by_country": [
    {"country": "US", "count": 25},
    {"country": "UK", "count": 12},
    {"country": "DE", "count": 5}
  ]
}
```

---

### Public Redirect Endpoint

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|-----------|
| GET | `/{short_code}/` | Redirect to original URL | None | 100/day (anon) |

Supports both short code and custom alias:
```bash
# Via short code
curl -X GET http://localhost:8000/abc123/ -L

# Via custom alias
curl -X GET http://localhost:8000/docs/ -L
```

Returns HTTP 302 redirect or:
- 404 if not found or inactive
- 410 if expired

---

### Health Check Endpoint

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|-----------|
| GET | `/health/` | Service health status | None | - |

**Response (200 - All services OK)**:
```json
{
  "status": "ok",
  "checks": {
    "db": "ok",
    "redis": "ok"
  }
}
```

**Response (503 - Degraded)**:
```json
{
  "status": "degraded",
  "checks": {
    "db": "ok",
    "redis": "error"
  }
}
```

Use this endpoint for:
- Load balancer health checks
- Kubernetes liveness/readiness probes
- Monitoring dashboards

---

## Authentication

### How JWT Auth Works

1. **Register or Login** → Get access + refresh tokens
2. **Include access token** in all protected requests:
```bash
Authorization: Bearer <access_token>
```

3. **Access token expires** after 60 minutes
   - Use refresh token to get a new access token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

4. **Logout** blacklists the refresh token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

### Using Swagger UI

1. Visit http://localhost:8000/api/docs/
2. Click **"Authorize"** button (top right)
3. Paste your access token in the format: `Bearer <token>`
4. Try requests directly in the UI

---

## Features by Module

### Module 5: Core URL Shortener
✅ Django project with PostgreSQL + Docker setup  
✅ URL generation with 6-char random codes  
✅ Deduplication (same URL = same code)  
✅ Public redirect endpoint (/{short_code}/)  
✅ OpenAPI documentation  

### Module 6: ORM & Data Layer
✅ User model with premium tier support  
✅ URL ownership and soft deletes  
✅ Click tracking with geographic data  
✅ Tag categorization (M2M relationships)  
✅ Query optimization (select_related, prefetch_related)  
✅ Analytics aggregation with ORM  

### Module 7: JWT Auth & Permissions
✅ JWT authentication (access + refresh tokens)  
✅ User registration with password validation  
✅ Role-based access control (free/premium/admin)  
✅ Free tier limits (10 URLs max)  
✅ Premium features (custom aliases, analytics)  
✅ Rate limiting (login: 5/min, create: 30/min)  
✅ Owner-only URL updates  
✅ Token blacklisting on logout  

### Module 8: Advanced Optimization & Production Readiness
✅ Redis caching with cache-aside pattern for 80%+ faster redirects  
✅ Celery async task queue for click tracking (non-blocking)  
✅ Celery Beat scheduled tasks (nightly URL expiry cleanup)  
✅ URL preview metadata fetched asynchronously after URL creation/update  
✅ JSON structured logging for error tracking and observability  
✅ Service health monitoring endpoint (database + Redis checks)  
✅ Django admin interface for operator management and data browsing  
✅ Domain-driven custom exceptions (URLLimitExceeded, PremiumFeatureRequired, AliasAlreadyTaken)  
✅ ACID-compliant transactions for multi-step database operations  
✅ Docker Compose services for Redis, Celery worker, and Celery Beat  
✅ Comprehensive test fixtures for isolated async and caching tests  

### Module 9: URL Preview Microservice
✅ Separate Django preview service for extracting page metadata  
✅ Preview endpoint returns title, description, and favicon from target URLs  
✅ Asynchronous dispatch from the main app using Celery + `transaction.on_commit()`  
✅ Redis-backed circuit breaker to avoid hammering failing domains  
✅ Fallback-safe parsing with BeautifulSoup and lxml  
✅ API responses include preview metadata once available  
✅ Dedicated Docker Compose service for the preview workerless microservice  

---

## Module 8 Technical Details

### Redis Caching (Cache-Aside Pattern)
```
Request for /{short_code}/
    │
    ├─→ Redis Cache (check)
    │      │
    │      ├─→ Cache HIT → Return cached URL → Redirect
    │      │
    │      └─→ Cache MISS → Database query
    │             │
    │             ├─→ URL found → Cache it (24h TTL) → Redirect
    │             └─→ URL not found → Return 404
```

**Benefits:**
- 80%+ reduction in database queries for popular short codes
- 24-hour TTL balances freshness with reduced load
- Automatic cache invalidation when URLs are updated/deactivated

### Celery Async Task Execution
```
User clicks /{short_code}/
    │
    ├─→ Redirect immediately (HTTP 302)
    │
    └─→ Async task dispatched
           │
           ├─→ track_click_task (Celery worker)
           │      └─→ Create Click record
           │      └─→ Increment URL.click_count (atomic transaction)
           │      └─→ Retry on failure (3 attempts with backoff)
```

**Benefits:**
- Non-blocking redirects (no I/O wait)
- Reliable click tracking with retry logic
- ACID compliance via `transaction.atomic()`

### Celery Beat Scheduled Tasks
- **Nightly cleanup** at 00:00 UTC: Deactivates URLs with `expires_at < now()`
- Configurable via `CELERY_BEAT_SCHEDULE` in settings
- Integrated logging for task tracking

### JSON Structured Logging
```json
{
  "time": "2026-05-10 17:52:29,839",
  "level": "WARNING",
  "logger": "django.request",
  "message": "Not Found: /abc123/",
  "short_code": "abc123"
}
```
- Enables log aggregation (ELK, Datadog, Splunk)
- ERROR+ logs from API and security modules
- Carries custom fields (short_code, url_id, etc.)

### Domain-Driven Exceptions
```python
# Instead of generic ValueError, use domain exceptions:
raise URLLimitExceeded("Free user exceeded 10-URL limit")
raise PremiumFeatureRequired("Custom aliases require premium tier")
raise AliasAlreadyTaken("Alias 'docs' is already taken")
```
Maps to HTTP status codes:
- `URLLimitExceeded` → 403 Forbidden
- `PremiumFeatureRequired` → 403 Forbidden
- `AliasAlreadyTaken` → 409 Conflict

### Health Check Endpoint
```
GET /api/v1/health/
    │
    ├─→ Database: SELECT 1
    └─→ Redis: SET "_health" "1" (5s TTL)
       │
       └─→ Return 200 (OK) or 503 (Degraded)
```

## Module 9 Technical Details

### Preview Metadata Pipeline
```
URL created or updated
    │
    ├─→ Transaction commits successfully
    │
    ├─→ on_commit() schedules fetch_url_preview_task
    │
    ├─→ Celery worker calls preview_service /api/preview/
    │
    ├─→ preview_service fetches and parses metadata
    │
    └─→ URL row updated with title, description, favicon
```

**Benefits:**
- Keeps URL creation fast while metadata loads in the background
- Avoids race conditions by dispatching only after the database commit completes
- Limits repeated failures with a per-domain circuit breaker in Redis
- Lets the main API return preview fields as soon as they are available

### Preview Service Endpoints
- `POST /api/preview/` on port 8001: fetches metadata for an arbitrary URL
- `GET /health/` on port 8001: lightweight service health check

### Preview Metadata Storage
- `title`, `description`, and `favicon` live on the `URL` model
- The fields are optional so URLs can exist before preview data is fetched
- The API serializer includes these fields in URL responses for the UI and clients

### Django Admin Interface
- **Operator Access**: Browse users, URLs, clicks without code access
- **Read-Only Auditing**: Click records immutable for compliance
- **Bulk Actions**: Deactivate multiple URLs at once
- **Filtering & Search**: Filter by tier, tags, country; search by username
- **Access**: http://localhost:8000/admin/ (staff users only)

---

## Database Schema

### User Model
```python
class User(AbstractUser):
    email: EmailField (unique)
    is_premium: BooleanField (default=False)
    tier: CharField (choices: free, premium, admin)
```

### URL Model
```python
class URL(Model):
    owner: ForeignKey(User) (nullable)
    original_url: URLField (max 2048)
    short_code: CharField (unique, indexed)
    custom_alias: CharField (unique, nullable, premium only)
    title: CharField (nullable)
    description: CharField (nullable)
    favicon: CharField (nullable)
    click_count: PositiveIntegerField
    is_active: BooleanField (soft delete)
    expires_at: DateTimeField (nullable)
    tags: ManyToManyField(Tag)
    created_at: DateTimeField (auto)
```

### Click Model (Analytics)
```python
class Click(Model):
    url: ForeignKey(URL)
    ip_address: GenericIPAddressField
    user_agent: TextField
    country: CharField
    city: CharField
    referrer: URLField
    clicked_at: DateTimeField (auto)
```

### Tag Model
```python
class Tag(Model):
    name: CharField (unique)
    urls: ManyToManyField(URL)
```

---

## Development

### Project Structure
```
Final-Project/
├── apps/
│   ├── api/
│   │   ├── throttles.py
│   │   └── v1/
│   │       ├── permissions.py
│   │       ├── auth/
│   │       │   ├── serializers.py
│   │       │   ├── views.py
│   │       │   └── urls.py
│   │       ├── links/
│   │       │   ├── serializers.py
│   │       │   ├── views.py
│   │       │   └── urls.py
│   │       ├── analytics/
│   │       │   ├── views.py
│   │       │   └── urls.py
│   │       └── urls.py
│   ├── core/
│   │   └── (placeholder)
│   ├── users/
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   └── migrations/
│   └── shortener/
│       ├── models.py
│       ├── managers.py
│       ├── selectors.py
│       ├── services.py
│       ├── analytics.py
│       ├── migrations/
│       └── tests/
├── config/
│   ├── settings/
│   │   ├── base.py (JWT, DRF, Spectacular config)
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

### Environment Variables
```bash
# .env.example - Django & Database
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.dev
DATABASE_URL=postgresql://user:password@db:5432/urlshortener
POSTGRES_DB=urlshortener
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
ALLOWED_HOSTS=localhost,127.0.0.1

# Module 8: Caching & Async Tasks
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Module 9: URL Preview Microservice
PREVIEW_SERVICE_URL=http://preview_service:8001
CORS_ALLOWED_ORIGINS=
CORS_ALLOW_ALL_ORIGINS=False
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300
```

**Module 8 Environment Breakdown:**
- `REDIS_URL`: Redis connection for cache-aside pattern (24-hour TTL for redirects)
- `CELERY_BROKER_URL`: Redis connection for Celery task queue (click tracking, cleanup)
- `CELERY_RESULT_BACKEND`: Redis for Celery task results (same broker for simplicity)

**Module 9 Environment Breakdown:**
- `PREVIEW_SERVICE_URL`: Base URL for the preview metadata microservice
- `CORS_ALLOWED_ORIGINS`: Exact frontend origins allowed to call the API in production
- `CORS_ALLOW_ALL_ORIGINS`: Development-friendly CORS toggle when no frontend origin list is needed
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD`: Number of preview failures before a domain is temporarily blocked
- `CIRCUIT_BREAKER_RECOVERY_TIMEOUT`: Cooldown window, in seconds, before retrying an open circuit

### Code Style
```bash
# Format code
poetry run black apps/ config/

# Lint code
poetry run ruff check apps/ config/

# Pre-commit hooks
pre-commit run --all-files
```

---

## Testing

### Run All Tests
```bash
poetry run pytest -v
```

### Run Specific Test Module
```bash
# Auth and permissions tests
poetry run pytest apps/api/tests/test_auth_and_permissions.py -v

# URL service tests
poetry run pytest apps/shortener/tests/test_services.py -v

# Specific test class
poetry run pytest apps/api/tests/test_auth_and_permissions.py::TestRegister -v

# With coverage
poetry run pytest --cov=apps --cov-report=html
```

### Test Coverage Includes
- ✅ User registration and validation
- ✅ JWT login/logout/refresh
- ✅ URL creation with tier limits
- ✅ Ownership permissions (read/write/delete)
- ✅ Premium feature gating (custom aliases, analytics)
- ✅ Rate limiting
- ✅ Analytics queries
- ✅ Click tracking
- ✅ Cache operations (set, get, invalidate)
- ✅ Async Celery tasks (click tracking, URL cleanup)
- ✅ Health check endpoint
- ✅ Admin interface access control

### Module 8 Testing: Pytest Fixtures

**conftest.py** provides two autouse fixtures for isolated testing:

```python
@pytest.fixture(autouse=True)
def use_locmem_cache(settings):
    """Use in-memory cache instead of Redis for tests."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    cache.clear()  # Clear before/after each test
    yield
    cache.clear()

@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Run Celery tasks synchronously for deterministic behavior."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
```

**Benefits:**
- No external Redis/Celery services required
- Tests run in seconds (not waiting for broker)
- Assertions can verify task side-effects immediately
- Cache doesn't pollute between test runs

---

## Common Tasks

### Create a Migration
```bash
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```

### Access Database Shell
```bash
# Via Docker
docker exec -it final-project-web-1 poetry run python manage.py dbshell

# Local PostgreSQL
psql -U postgres -d urlshortener
```

### Check Migrations Status
```bash
poetry run python manage.py showmigrations
```

### Reset Database (development only)
```bash
poetry run python manage.py flush
```

---

## API Response Status Codes

| Status | Meaning |
|--------|---------|
| 200 | OK (successful GET/PUT/PATCH) |
| 201 | Created (successful POST) |
| 204 | No Content (successful DELETE) |
| 302 | Found (redirect to original URL) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid auth) |
| 403 | Forbidden (permission denied, tier limit, rate limit) |
| 404 | Not Found (resource doesn't exist) |
| 410 | Gone (URL expired) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error |

---

## Troubleshooting

### Database Connection Error
```bash
# Ensure Postgres is running
docker compose ps

# Check logs
docker compose logs db
```

### Port Already in Use
```bash
# Change port in docker-compose.yml
# Or kill process on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### JWT Token Expired
```bash
# Use refresh token to get new access token
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

### Migrations Not Applied
```bash
poetry run python manage.py migrate
docker compose restart web
```

---

## License

This project is provided as-is for educational purposes.

---

## Support

For issues or questions:
1. Check the error message and status code
2. Review this README's troubleshooting section
3. Check test files for usage examples
4. Visit Swagger UI at `/api/docs/` for interactive API exploration
