# URL Shortener API (Django 5 + PostgreSQL)

Production-grade URL shortening service with JWT auth, user tiers, analytics, preview metadata, and microservices architecture.

## Quick Facts

| Feature | Details |
|---------|---------|
| **Tech Stack** | Django 5, DRF, PostgreSQL, Redis, Celery, Docker |
| **Auth** | JWT + RBAC (free/premium/admin tiers) |
| **Features** | Short codes, custom aliases, analytics, preview metadata, async tasks |
| **Microservices** | Separate preview service (port 8001) |
| **Deployment** | Docker Compose, Kubernetes-ready |
| **Tests** | 243 tests passing |


## Quick Start (5 minutes)

### With Docker (Recommended)
```bash
git clone <repo-url> && cd Final-Project
cp .env.example .env
docker compose up --build
```

**Access:**
- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/
- Preview Service: http://localhost:8001/health/

### Without Docker
```bash
poetry install && poetry run python manage.py migrate
poetry run python manage.py runserver
```

For async tasks/caching, start Redis and Celery in separate terminals.

---

## Example API Calls

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","email":"user@example.com","password":"Pass123!","password_confirm":"Pass123!"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Pass123!"}'
```

**Create short URL:**
```bash
curl -X POST http://localhost:8000/api/v1/urls/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"original_url":"https://example.com/long/path"}'
```

**Response:**
```json
{
  "short_code": "abc123",
  "short_url": "http://localhost:8000/abc123/",
  "original_url": "https://example.com/long/path",
  "click_count": 0,
  "title": null,
  "description": null,
  "favicon": null
}
```

Preview metadata (title, description, favicon) populates asynchronously via Celery.

---

## Features

- ✅ **URL Shortening**: 6-char random codes with deduplication
- ✅ **Tier-Based Access**: Free (10 URLs), Premium (unlimited + custom aliases + analytics), Admin
- ✅ **Analytics**: Click counts by country (premium only)
- ✅ **Preview Metadata**: Auto-extract title, description, favicon from target URLs
- ✅ **JWT Authentication**: Access + refresh tokens with rotation & blacklisting
- ✅ **Async Tasks**: Celery for click tracking, preview fetching, nightly cleanup
- ✅ **Redis Caching**: 80%+ faster redirects via cache-aside pattern
- ✅ **SSRF Protection**: Circuit-breaker, IP ranges, timeouts, size limits
- ✅ **Rate Limiting**: Login (10/min), URL create (10/min), per-endpoint throttles
- ✅ **OpenAPI Docs**: Swagger UI at /api/docs/
- ✅ **Health Checks**: Database + Redis status endpoint
- ✅ **Admin Interface**: Staff management, click auditing, bulk operations

---

## Architecture Overview

```
┌──────────────────────────────────────┐
│       Client (Web/Mobile/API)        │
└───────────────┬──────────────────────┘
                │
    ┌───────────┴──────────┐
    ▼                      ▼
┌─────────────┐   ┌──────────────────────┐
│  Main API   │   │ Preview Microservice │
│ (port 8000) │   │  (port 8001, no DB)  │
│             │   │                      │
│ • Auth      │   │ • HTML parsing (BS4) │
│ • URLs      │   │ • Metadata extract   │
│ • Analytics │   │ • SSRF mitigation    │
└─────┬───────┘   └──────────────────────┘
      │
   ┌──┴──┬──────┬──────────┐
   ▼     ▼      ▼          ▼
  PG   Redis Celery  Celery Beat
  DB    Cache Worker  Scheduler
```

**Topology:**
- **Main API** (web): Handles auth, URL CRUD, analytics, redirects
- **Preview Service** (preview_service): Isolated microservice, stateless, can scale independently
- **PostgreSQL** (db): Primary data store, 15+ optimized indexes
- **Redis** (redis): Cache-aside pattern (24h TTL), Celery broker, circuit-breaker
- **Celery Worker** (celery): Async tasks—track clicks, fetch previews, cleanup expired URLs
- **Celery Beat** (celery-beat): Nightly URL expiry cleanup (00:00 UTC)

---

## Key Endpoints

| GET | `/health/` | Service status (DB + Redis checks) | None |
| POST | `/api/preview/` (port 8001) | Extract page metadata | None |

**Rate Limits:**
| Endpoint | Limit | Scope |
|----------|-------|-------|
| Login | 10/min | Per IP |
| Create URL | 10/min | Per user |
| Redirect | 100/day | Per IP |

---

## Authentication Flow

1. **Register/Login** → Get access + refresh tokens
2. **Attach token**: `Authorization: Bearer <access_token>`
3. **Token expires** after 60 minutes → Use refresh token to get new access token
4. **Logout** → Blacklists refresh token

**Try in Swagger:**
1. Visit http://localhost:8000/api/docs/
2. Click **"Authorize"** button
3. Enter: `Bearer YOUR_ACCESS_TOKEN`
4. Execute requests directly in the UI

---

## Project Structure

```
Final-Project/
├── apps/
│   ├── api/                 # REST API layer
│   │   ├── throttles.py     # Rate limiting (login 10/min, create 10/min)
│   │   └── v1/
│   │       ├── permissions.py
│   │       ├── auth/        # Registration, login, logout, refresh
│   │       ├── links/       # URL CRUD + analytics
│   │       └── analytics/   # Premium analytics queries
│   ├── shortener/           # URL shortening domain
│   │   ├── models.py        # URL, Click, Tag
│   │   ├── services.py      # Business logic (tier limits, deduplication)
│   │   ├── selectors.py     # Read-only queries
│   │   ├── circuit_breaker.py  # Redis-backed circuit breaker
│   │   └── tasks.py         # Celery async tasks
│   └── users/               # User & tier management
│       ├── models.py        # User with tier choices
│       ├── services.py      # User creation/validation
│       └── selectors.py     # User queries
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared (JWT, DRF, Spectacular, Celery)
│   │   ├── dev.py           # Development overrides
│   │   └── prod.py          # Production overrides
│   ├── urls.py              # Main API routing
│   ├── wsgi.py              # WSGI entry
│   └── celery.py            # Celery setup
├── preview_service/         # Separate microservice (port 8001)
│   ├── config/
│   │   ├── settings.py      # Minimal (no DB, no cache)
│   │   ├── urls.py          # Preview routes
│   │   └── wsgi.py          # Preview WSGI entry
│   ├── views.py             # HTML parsing, metadata extraction
│   └── tests/               # Service tests (mocked)
├── tests/                   # Integration tests
│   ├── conftest.py          # pytest fixtures (cache, celery)
│   ├── test_django_setup.py
│   ├── test_schema.py
│   ├── test_services.py
│   └── test_views.py
├── docker-compose.yml       # Multi-service orchestration
├── Dockerfile
├── manage.py
├── pyproject.toml           # Poetry dependencies
└── .env.example             # Environment template
```

---

## Environment Variables

**Core Django:**
```bash
SECRET_KEY=<generate-with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'>
DEBUG=True              # False in production
DJANGO_SETTINGS_MODULE=config.settings.dev
DATABASE_URL=postgresql://user:password@db:5432/urlshortener
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Module 8 (Cache & Async):**
```bash
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

**Module 9 (Preview Service):**
```bash
PREVIEW_SERVICE_URL=http://preview_service:8001
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5      # Failures before blocking domain
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300     # Seconds before retry
```

**Security (Production):**
```bash
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## Common Commands

**Run Tests:**
```bash
poetry run pytest -v                              # All tests
poetry run pytest apps/api/tests/ -v              # Auth & API tests
poetry run pytest --cov=apps --cov-report=html   # With coverage
```

**Database:**
```bash
poetry run python manage.py migrate              # Apply migrations
poetry run python manage.py makemigrations       # Create migrations
poetry run python manage.py shell                # Django shell
docker compose exec db psql -U postgres -d urlshortener  # Direct DB access
```

**Docker:**
```bash
docker compose up --build                        # Build & start
docker compose logs -f                           # View all logs
docker compose logs -f web                       # Specific service
docker compose down                              # Stop & cleanup
```

**Development:**
```bash
poetry run black apps/ config/                   # Format code
poetry run ruff check apps/ config/              # Lint
poetry run python manage.py check                # Django system check
```

---

## API Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST (new URL) |
| 400 | Bad Request | Invalid JSON, validation error |
| 401 | Unauthorized | Missing/expired token |
| 403 | Forbidden | Permission denied, tier limit, rate limit |
| 404 | Not Found | URL doesn't exist |
| 410 | Gone | URL expired |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Database/code issue |

---

## Troubleshooting

**Container won't start?**
```bash
docker compose logs web  # Check error
docker compose down && docker compose up --build  # Rebuild
```

**Database connection failed?**
```bash
docker compose ps db                    # Verify running
docker compose exec db psql -U postgres # Test connection
```

**Redis not responding?**
```bash
docker compose exec redis redis-cli ping  # Should return PONG
docker compose restart redis             # Restart if needed
```

**Celery tasks not running?**
```bash
docker compose logs celery                # Check worker logs
docker compose restart celery celery-beat # Restart tasks
```

**Rate limited (429 error)?**
```
Wait 1 minute for throttle to reset. Default: login 10/min, create 10/min.
Disable throttles in dev: REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
```

**Tests failing?**
```bash
poetry run pytest --lf -v               # Run last failed
poetry run pytest -k test_name -v       # Run specific test
poetry run pytest -x                    # Stop on first failure
```

---

## Testing

**Coverage:** 243 tests passing  
**Fixtures:** In-memory cache + eager Celery execution (no external services needed)

**Key test areas:**
- User registration, login, token refresh, logout
- URL CRUD with tier-based permissions
- Free tier limits (10 URLs max)
- Premium features (custom aliases, analytics)
- Click tracking async task
- Cache-aside pattern
- Preview service circuit-breaker
- Rate limiting
- Health check endpoint

---

## Modules Overview

| Module | Focus | Key Tech |
|--------|-------|----------|
| 5 | URL generation | Django ORM, indexes |
| 6 | Data layer | Models, relationships, queries |
| 7 | JWT + RBAC | djangorestframework-simplejwt, permissions, throttling |
| 8 | Caching & async | Redis, Celery, circuit-breaker, logging |
| 9 | Preview metadata | HTML parsing, SSRF mitigation, microservice |

---

## Production Deployment

### Checklist

- [ ] Set `SECRET_KEY` to secure random value
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS` to your domain(s)
- [ ] Use HTTPS + set `SECURE_SSL_REDIRECT = True`
- [ ] Use managed PostgreSQL (RDS, DigitalOcean, Heroku)
- [ ] Use managed Redis (ElastiCache, DigitalOcean, Heroku)
- [ ] Configure backups & point-in-time recovery
- [ ] Set centralized logging (ELK, Datadog, Splunk)
- [ ] Set up monitoring & alerts (Prometheus, New Relic)
- [ ] Configure health checks for load balancers
- [ ] Use Docker registry (Docker Hub, ECR, GCR)
- [ ] Deploy with Kubernetes or Docker Swarm

### Docker Image Build

```bash
docker build -t myregistry/urlshortener:latest \
  --build-arg BUILD_TARGET=production \
  -f Dockerfile .

docker push myregistry/urlshortener:latest
```

### Kubernetes Example
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/yyyyy

# Logging
LOG_LEVEL=INFO
```

### Kubernetes Deployment (Example)

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: urlshortener-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: urlshortener-api
  template:
    metadata:
      labels:
        app: urlshortener-api
    spec:
      containers:
      - name: api
        image: myregistry/urlshortener-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: urlshortener-secrets
              key: secret_key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: urlshortener-secrets
              key: database_url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: urlshortener-secrets
              key: redis_url
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: urlshortener-celery
spec:
  replicas: 2
  selector:
    matchLabels:
      app: urlshortener-celery
  template:
    metadata:
      labels:
        app: urlshortener-celery
    spec:
      containers:
      - name: worker
        image: myregistry/urlshortener-api:latest
        command: ["celery", "-A", "config", "worker", "-l", "info"]
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: urlshortener-secrets
              key: redis_url
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: urlshortener-preview
spec:
  replicas: 2
  selector:
    matchLabels:
      app: urlshortener-preview
  template:
    metadata:
      labels:
        app: urlshortener-preview
    spec:
      containers:
      - name: preview
        image: myregistry/urlshortener-preview:latest
        ports:
        - containerPort: 8001
        livenessProbe:
          httpGet:
            path: /health/
            port: 8001
          initialDelaySeconds: 20
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

### Health Monitoring Post-Deployment

```bash
# Check main API health
curl https://yourdomain.com/health/

# Check preview service health
curl https://yourdomain.com/preview-health/
# OR if separate:
curl https://preview-api.yourdomain.com/health/

# Check Celery queue depth
curl https://yourdomain.com/api/admin/celery-stats/  # (if admin endpoint exists)
```

### Database Migration on Deploy

```bash
# Using Django management command (can be called from init container)
python manage.py migrate --noinput

# Or via bash script:
docker exec urlshortener-api python manage.py migrate --noinput
```

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
