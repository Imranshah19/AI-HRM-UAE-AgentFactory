# SECTION 9 — DEPLOYMENT PLAN

## 9.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: "3.9"

x-common-env: &common-env
  DATABASE_URL: postgresql+asyncpg://hrms:hrms_dev@postgres:5432/hrms_dev
  REDIS_URL: redis://redis:6379/0
  ELASTICSEARCH_URL: http://elasticsearch:9200
  S3_ENDPOINT_URL: http://minio:9000
  S3_ACCESS_KEY: minioadmin
  S3_SECRET_KEY: minioadmin
  S3_BUCKET_NAME: hrms-dev
  JWT_SECRET_KEY: dev_secret_key_minimum_32_characters_long_for_hmac
  ENVIRONMENT: development
  LOG_LEVEL: DEBUG
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2

services:

  # ── PostgreSQL ──────────────────────────────────────────────────────
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: hrms_dev
      POSTGRES_USER: hrms
      POSTGRES_PASSWORD: hrms_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hrms -d hrms_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── Redis ──────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # ── Elasticsearch ──────────────────────────────────────────────────
  elasticsearch:
    image: elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q 'status.*green\\|yellow'"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ── MinIO (S3-compatible local storage) ────────────────────────────
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ── MinIO bucket setup ─────────────────────────────────────────────
  minio-setup:
    image: minio/mc
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 minioadmin minioadmin;
      mc mb local/hrms-dev --ignore-existing;
      mc anonymous set download local/hrms-dev/public/;
      exit 0;"

  # ── FastAPI Backend ────────────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
      target: development
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app     # hot reload
    environment:
      <<: *common-env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/system/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ── Celery Worker (default queue) ──────────────────────────────────
  celery-worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
      target: development
    command: >
      celery -A app.celery_app worker
      --loglevel=info
      --concurrency=4
      --queues=default,notifications,payroll,reports,ai
    volumes:
      - ./backend:/app
    environment:
      <<: *common-env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # ── Celery Beat (scheduler for cron notifications) ─────────────────
  celery-beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
      target: development
    command: celery -A app.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app
    environment:
      <<: *common-env
    depends_on:
      - celery-worker

  # ── Celery Flower (monitoring) ─────────────────────────────────────
  flower:
    image: mher/flower:2.0
    command: celery flower --port=5555 --broker=redis://redis:6379/1
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
    ports:
      - "5555:5555"
    depends_on:
      - redis

  # ── Next.js Frontend ───────────────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
      target: development
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_WS_URL: ws://localhost:8000
      NEXTAUTH_SECRET: dev_nextauth_secret
      NEXTAUTH_URL: http://localhost:3000
    ports:
      - "3000:3000"
    depends_on:
      - api

  # ── Nginx (reverse proxy — matches prod config) ────────────────────
  nginx:
    image: nginx:alpine
    volumes:
      - ./docker/nginx/dev.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "80:80"
    depends_on:
      - api
      - frontend

volumes:
  postgres_data:
  redis_data:
  es_data:
  minio_data:
```

---

## 9.2 Dockerfiles

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim as base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Development stage ──────────────────────────────────────────────
FROM base as development
RUN pip install watchfiles pytest pytest-asyncio httpx factory-boy
COPY backend/ .
EXPOSE 8000

# ── Production stage ───────────────────────────────────────────────
FROM base as production
# Non-root user for security
RUN addgroup --system hrms && adduser --system --group hrms
COPY --chown=hrms:hrms backend/ .
USER hrms

# Gunicorn with uvicorn workers
RUN pip install gunicorn
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/system/health || exit 1
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--timeout", "120"]
```

```dockerfile
# docker/Dockerfile.frontend
FROM node:20-alpine as base
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

# ── Development ────────────────────────────────────────────────────
FROM base as development
COPY frontend/ .
EXPOSE 3000

# ── Builder ────────────────────────────────────────────────────────
FROM base as builder
COPY frontend/ .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Production ─────────────────────────────────────────────────────
FROM node:20-alpine as production
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system nextjs && adduser --system --group nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s \
    CMD wget -qO- http://localhost:3000/api/health || exit 1
CMD ["node", "server.js"]
```

---

## 9.3 Kubernetes Deployment YAML (Production)

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: hrms-production
  labels:
    app: hrms
    env: production

---
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hrms-api
  namespace: hrms-production
  labels:
    app: hrms-api
    version: "1.0.0"
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1         # one extra pod during update
      maxUnavailable: 0   # zero downtime — always keep 3 running
  selector:
    matchLabels:
      app: hrms-api
  template:
    metadata:
      labels:
        app: hrms-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: hrms-api-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: hrms-api
        image: ECR_REGISTRY/hrms-api:IMAGE_TAG
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: hrms-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: hrms-secrets
              key: jwt-secret-key
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: hrms-secrets
              key: redis-url
        - name: ELASTICSEARCH_URL
          valueFrom:
            secretKeyRef:
              name: hrms-secrets
              key: elasticsearch-url
        readinessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          failureThreshold: 3
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]  # drain in-flight requests
      terminationGracePeriodSeconds: 60

---
# k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: hrms-api-svc
  namespace: hrms-production
spec:
  selector:
    app: hrms-api
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP

---
# k8s/hpa.yaml (already shown in Section 12, abbreviated here)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hrms-api-hpa
  namespace: hrms-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hrms-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 65

---
# k8s/celery-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hrms-celery-default
  namespace: hrms-production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hrms-celery-default
  template:
    metadata:
      labels:
        app: hrms-celery-default
    spec:
      containers:
      - name: celery
        image: ECR_REGISTRY/hrms-api:IMAGE_TAG
        command: ["celery", "-A", "app.celery_app", "worker",
                  "--loglevel=info", "--concurrency=4",
                  "--queues=default,notifications"]
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: hrms-secrets
              key: database-url

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hrms-ingress
  namespace: hrms-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"    # for file uploads
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300" # for payroll runs
    # Rate limiting at nginx level (per IP)
    nginx.ingress.kubernetes.io/limit-rps: "50"
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "3"
spec:
  tls:
  - hosts:
    - api.hrms.company.com
    - app.hrms.company.com
    secretName: hrms-tls
  rules:
  - host: api.hrms.company.com
    http:
      paths:
      - path: /api/
        pathType: Prefix
        backend:
          service:
            name: hrms-api-svc
            port:
              number: 80
      - path: /ws/
        pathType: Prefix
        backend:
          service:
            name: hrms-api-svc
            port:
              number: 80
  - host: app.hrms.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: hrms-frontend-svc
            port:
              number: 80
```

---

## 9.4 Alembic Database Migration Strategy

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
from app.models import Base  # Import all models
import os

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    # Use sync URL for migrations (asyncpg → psycopg2)
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql://")

def run_migrations_offline():
    """Run migrations in 'offline' mode — generates SQL script without DB connection."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # detect column type changes
        compare_server_default=True, # detect default value changes
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations with live DB connection."""
    from sqlalchemy import create_engine
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Migration Workflow Commands
```bash
# Create new migration (auto-detect changes from models)
alembic revision --autogenerate -m "add_feature_flags_table"

# Review generated migration before applying
cat alembic/versions/abc123_add_feature_flags_table.py

# Apply all pending migrations (development)
alembic upgrade head

# Apply one step at a time (careful production)
alembic upgrade +1

# Check current version
alembic current

# Show pending migrations
alembic history --verbose

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Generate SQL script for DBA review (offline mode)
alembic upgrade head --sql > migration_2024_01.sql
```

### Zero-Downtime Migration Rules
```python
# alembic/versions/20240115_add_column_with_default.py
"""
SAFE zero-downtime migration patterns:

SAFE (backward compatible):
  ✅ op.add_column with nullable=True and no server_default
  ✅ op.add_column with nullable=False and server_default (DB fills existing rows)
  ✅ op.create_index (concurrent=True avoids table lock)
  ✅ op.create_table (new table, no impact)

UNSAFE (requires maintenance window OR multi-step migration):
  ❌ op.drop_column (old code still references it)
  ❌ op.alter_column (type changes lock table)
  ❌ op.rename_column (old code breaks immediately)
  ❌ op.add_column with nullable=False and no default (locks table for backfill)

SAFE drop_column pattern (3-step over 3 deployments):
  Step 1: Remove column from code (stop reading/writing it)
  Step 2: Deploy Step 1 → column still exists, just unused
  Step 3: Drop column in migration (now safe, nothing references it)
"""

def upgrade():
    # SAFE: Add nullable column, no default needed
    op.add_column("employees",
        sa.Column("secondary_manager_id", postgresql.UUID(), nullable=True)
    )
    # SAFE: Create index concurrently (no table lock)
    op.execute(
        "CREATE INDEX CONCURRENTLY idx_employees_secondary_mgr "
        "ON employees(secondary_manager_id)"
    )

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_employees_secondary_mgr")
    op.drop_column("employees", "secondary_manager_id")
```

---

## 9.5 Environment Variable Strategy

```bash
# ── Development (.env.development) — NEVER commit to git ──────────
DATABASE_URL=postgresql+asyncpg://hrms:hrms_dev@localhost:5432/hrms_dev
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=hrms-dev
JWT_SECRET_KEY=dev_secret_key_at_least_32_chars_for_hs256_hmac
ENVIRONMENT=development
LOG_LEVEL=DEBUG
SENDGRID_API_KEY=SG.dev_key_here
TWILIO_ACCOUNT_SID=dev_sid
TWILIO_AUTH_TOKEN=dev_token
OPENAI_API_KEY=sk-dev-key

# ── Production — NEVER in .env files — Stored in Vault/Secrets Manager ──
# Secrets fetched at startup from HashiCorp Vault:
# vault kv get -field=value secret/hrms/production/database-url
# Injected as environment variables by K8s via ExternalSecrets operator
```

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    APP_VERSION: str = Field(default="1.0.0")

    # Database
    DATABASE_URL: str = Field(..., description="Async PostgreSQL URL")
    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_TIMEOUT: int = Field(default=30)

    # Redis
    REDIS_URL: str = Field(...)
    REDIS_TTL_DEFAULT: int = Field(default=300)

    # JWT
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Security
    ALLOWED_HOSTS: list[str] = Field(default=["*"])
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # AWS / S3
    AWS_REGION: str = Field(default="ap-south-1")
    S3_BUCKET_NAME: str = Field(...)
    S3_ENDPOINT_URL: str | None = Field(default=None)  # None = real AWS S3

    # Email
    SENDGRID_API_KEY: str = Field(default="")
    FROM_EMAIL: str = Field(default="hr@company.com")

    # AI
    OPENAI_API_KEY: str = Field(default="")

    # Feature Flags
    FLAG_CACHE_TTL_SECONDS: int = Field(default=300)

    @validator("DATABASE_URL")
    def validate_db_url(cls, v):
        if "asyncpg" not in v and "postgresql" not in v:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — reads env vars once at startup."""
    return Settings()
```

---

## 9.6 Zero-Downtime Rolling Update Procedure

```bash
#!/bin/bash
# scripts/deploy_production.sh

set -euo pipefail

IMAGE_TAG=$1
NAMESPACE="hrms-production"
DEPLOYMENT="hrms-api"

echo "🚀 Starting zero-downtime deployment — tag: $IMAGE_TAG"

# 1. Run database migrations FIRST (before deploying new code)
#    Migrations must be backward compatible with current running code
echo "📦 Running database migrations..."
kubectl exec -n $NAMESPACE \
  $(kubectl get pod -n $NAMESPACE -l app=hrms-api -o jsonpath="{.items[0].metadata.name}") \
  -- alembic upgrade head

echo "✅ Migrations applied"

# 2. Update the image (triggers rolling update with maxUnavailable=0)
echo "🔄 Rolling update starting..."
kubectl set image deployment/$DEPLOYMENT \
  hrms-api=ECR_REGISTRY/hrms-api:$IMAGE_TAG \
  -n $NAMESPACE

# 3. Wait for rollout to complete
kubectl rollout status deployment/$DEPLOYMENT \
  -n $NAMESPACE \
  --timeout=300s

# 4. Verify health
echo "🏥 Verifying health..."
sleep 10
HEALTH=$(kubectl exec -n $NAMESPACE \
  $(kubectl get pod -n $NAMESPACE -l app=hrms-api -o jsonpath="{.items[0].metadata.name}") \
  -- curl -s http://localhost:8000/api/v1/system/health)

if echo $HEALTH | grep -q '"status":"ok"'; then
  echo "✅ Deployment successful — all pods healthy"
else
  echo "❌ Health check failed — rolling back..."
  kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
  kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE
  exit 1
fi

# 5. Update Celery workers (after API is stable)
echo "🔄 Updating Celery workers..."
kubectl set image deployment/hrms-celery-default \
  celery=ECR_REGISTRY/hrms-api:$IMAGE_TAG \
  -n $NAMESPACE

kubectl rollout status deployment/hrms-celery-default \
  -n $NAMESPACE --timeout=120s

echo "🎉 Deployment complete — $IMAGE_TAG is live in production"
```
