# URL Shortener API (Django 5 + PostgreSQL)

A production-grade URL shortening service with JWT authentication, user tiers, analytics, and API documentation.

## Table of Contents
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Features by Module](#features-by-module)
- [Database Schema](#database-schema)
- [Development](#development)
- [Testing](#testing)

## Tech Stack

- **Backend**: Python 3.10, Django 5.x, Django REST Framework
- **Database**: PostgreSQL 15
- **Authentication**: JWT via `djangorestframework-simplejwt`
- **API Docs**: drf-spectacular (OpenAPI 3.0 + Swagger UI)
- **Containerization**: Docker & Docker Compose
- **Dependency Management**: Poetry
- **Testing**: pytest & pytest-django
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

3. **Access the application**:
- API: http://localhost:8000/api/v1/
- Swagger UI (API Docs): http://localhost:8000/api/docs/
- Schema (OpenAPI JSON): http://localhost:8000/api/schema/

4. **Stop services**:
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

6. **Run tests**:
```bash
poetry run pytest -v
```

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
│  │      Business Logic Layer (apps/shortener)      │   │
│  │  • services.py: Core URL creation/update logic  │   │
│  │  • selectors.py: Optimized query helpers        │   │
│  │  • analytics.py: Click stats aggregation        │   │
│  │  • permissions.py: Authorization rules          │   │
│  │  • throttles.py: Rate limiting                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │        Data Access Layer (ORM + Indexes)         │   │
│  │  • models.py: User, URL, Click, Tag             │   │
│  │  • managers.py: QuerySet helpers                │   │
│  │  • migrations: Schema versioning                │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                        │
│                                                          │
│  • users table (User model)                            │
│  • urls table (URL model) + indexes                    │
│  • clicks table (Click analytics)                      │
│  • tags table + M2M relationship                       │
│  • token_blacklist (JWT logout support)               │
└─────────────────────────────────────────────────────────┘
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
│   │   └── v1/
│   │       ├── auth_serializers.py
│   │       ├── auth_views.py
│   │       ├── url_serializers.py
│   │       ├── url_views.py
│   │       └── urls.py
│   ├── core/
│   │   └── (placeholder)
│   └── shortener/
│       ├── models.py
│       ├── managers.py
│       ├── selectors.py
│       ├── services.py
│       ├── analytics.py
│       ├── permissions.py
│       ├── throttles.py
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
# .env.example
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.dev
DATABASE_URL=postgresql://user:password@db:5432/urlshortener
POSTGRES_DB=urlshortener
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
ALLOWED_HOSTS=localhost,127.0.0.1
```

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
