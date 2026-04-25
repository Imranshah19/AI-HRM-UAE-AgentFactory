# AI-HRMS Production Deployment Guide

**Target OS:** Ubuntu 22.04 LTS
**Deployment Method:** Docker Compose (production configuration)
**Estimated Setup Time:** 60–90 minutes

---

## Table of Contents

1. [Server Requirements](#1-server-requirements)
2. [Server Setup](#2-server-setup)
3. [Clone Repository & Configure Environment](#3-clone-repository--configure-environment)
4. [Production Docker Compose](#4-production-docker-compose)
5. [Run Database Migrations](#5-run-database-migrations)
6. [Seed Superadmin](#6-seed-superadmin)
7. [Nginx Reverse Proxy Configuration](#7-nginx-reverse-proxy-configuration)
8. [SSL with Let's Encrypt (Certbot)](#8-ssl-with-lets-encrypt-certbot)
9. [Systemd Auto-Restart Service](#9-systemd-auto-restart-service)
10. [PostgreSQL Backup Script](#10-postgresql-backup-script)
11. [Monitoring](#11-monitoring)
12. [Rollback Procedure](#12-rollback-procedure)

---

## 1. Server Requirements

### Minimum (up to ~100 employees)
| Resource | Minimum |
|----------|---------|
| CPU | 4 vCPU |
| RAM | 8 GB |
| Disk | 50 GB SSD |
| OS | Ubuntu 22.04 LTS |
| Network | 100 Mbps, static IP |

### Recommended (100–1000 employees)
| Resource | Recommended |
|----------|-------------|
| CPU | 8 vCPU |
| RAM | 16 GB |
| Disk | 100 GB SSD (+ separate volume for uploads) |
| OS | Ubuntu 22.04 LTS |
| Network | 1 Gbps, static IP |

### Cloud Provider Examples
- **AWS:** t3.xlarge (4 vCPU, 16GB) or c5.2xlarge
- **GCP:** n2-standard-4 or n2-standard-8
- **DigitalOcean:** Droplet — General Purpose 8 GB
- **Azure:** Standard_D4s_v3

### Port Requirements (Firewall / Security Group)
| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH (restrict to admin IPs only) |
| 80 | TCP | HTTP (Nginx, redirects to HTTPS) |
| 443 | TCP | HTTPS (Nginx) |
| 5432 | TCP | PostgreSQL (optional, for remote admin; keep closed in production) |

---

## 2. Server Setup

SSH into your server as root or a sudo user, then run all commands below.

### 2.1 Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release
```

### 2.2 Install Docker

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (avoids needing sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 2.3 Install Docker Compose (standalone, if needed)

```bash
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 2.4 Install Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 2.5 Install Certbot (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2.6 Configure System Limits

```bash
# Increase file descriptor limits for production
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "fs.file-max = 2097152" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 3. Clone Repository & Configure Environment

### 3.1 Create Application Directory

```bash
sudo mkdir -p /opt/ai-hrms
sudo chown $USER:$USER /opt/ai-hrms
cd /opt/ai-hrms
```

### 3.2 Clone Repository

```bash
git clone https://github.com/your-org/ai-hrms.git .
# Or with SSH:
# git clone git@github.com:your-org/ai-hrms.git .
```

### 3.3 Copy and Edit Environment File

```bash
cp .env.example .env
vim .env   # or nano .env
```

### 3.4 .env.example (Reference)

Create `/opt/ai-hrms/.env.example` with the following content (copy to `.env` and fill in real values):

```env
# ─────────────────────────────────────────────────────────────────────────────
# AI-HRMS Production Environment Configuration
# Copy this file to .env and fill in real values before deploying.
# NEVER commit .env to version control.
# ─────────────────────────────────────────────────────────────────────────────

# ── Application ───────────────────────────────────────────────────────────────
APP_ENV=production
DEBUG=false
APP_NAME=AI-HRMS
APP_VERSION=1.3.0
SECRET_KEY=CHANGE_ME_generate_with_openssl_rand_hex_32

# ── Backend URLs ──────────────────────────────────────────────────────────────
BACKEND_URL=https://api.your-domain.com
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com

# ── PostgreSQL ────────────────────────────────────────────────────────────────
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=hrms_user
POSTGRES_PASSWORD=CHANGE_ME_strong_db_password
POSTGRES_DB=hrms_db
DATABASE_URL=postgresql+asyncpg://hrms_user:CHANGE_ME_strong_db_password@postgres:5432/hrms_db
DATABASE_SYNC_URL=postgresql://hrms_user:CHANGE_ME_strong_db_password@postgres:5432/hrms_db

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME_redis_password
REDIS_URL=redis://:CHANGE_ME_redis_password@redis:6379/0
CELERY_BROKER_URL=redis://:CHANGE_ME_redis_password@redis:6379/1
CELERY_RESULT_BACKEND=redis://:CHANGE_ME_redis_password@redis:6379/2

# ── JWT Authentication ────────────────────────────────────────────────────────
JWT_SECRET_KEY=CHANGE_ME_generate_with_openssl_rand_hex_64
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ── File Storage ──────────────────────────────────────────────────────────────
STORAGE_BACKEND=local
# For S3: STORAGE_BACKEND=s3
LOCAL_UPLOAD_DIR=/uploads
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_S3_BUCKET=hrms-uploads
# AWS_S3_REGION=ap-south-1

# ── First Superadmin (seeded on first run) ────────────────────────────────────
FIRST_SUPERADMIN_EMAIL=admin@your-domain.com
FIRST_SUPERADMIN_PASSWORD=CHANGE_ME_Admin@1234!
FIRST_SUPERADMIN_FIRST_NAME=System
FIRST_SUPERADMIN_LAST_NAME=Admin

# ── Email (SendGrid) ──────────────────────────────────────────────────────────
EMAIL_FROM=noreply@your-domain.com
EMAIL_FROM_NAME=AI-HRMS
SENDGRID_API_KEY=SG.CHANGE_ME

# ── SMS (Twilio) ──────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=CHANGE_ME
TWILIO_AUTH_TOKEN=CHANGE_ME
TWILIO_FROM_NUMBER=+1XXXXXXXXXX

# ── AI / OpenAI ───────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-CHANGE_ME
OPENAI_MODEL=gpt-4o-mini

# ── Next.js Frontend ──────────────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_APP_NAME=AI-HRMS
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com

# ── Monitoring (optional) ─────────────────────────────────────────────────────
# SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 3.5 Generate Secure Keys

```bash
# Generate JWT_SECRET_KEY
openssl rand -hex 64

# Generate SECRET_KEY
openssl rand -hex 32

# Generate a strong PostgreSQL password
openssl rand -base64 24

# Generate Redis password
openssl rand -base64 16
```

Fill these into your `.env` file before proceeding.

---

## 4. Production Docker Compose

The production compose file is `docker-compose.prod.yml` in the repository root.

### 4.1 Build and Start All Services

```bash
cd /opt/ai-hrms

# Pull pre-built images or build from source
docker compose -f docker-compose.prod.yml build --no-cache

# Start all services in detached mode
docker compose -f docker-compose.prod.yml up -d

# Check service status
docker compose -f docker-compose.prod.yml ps
```

### 4.2 Verify All Services Are Healthy

```bash
# Watch until all services are healthy (Ctrl+C to stop watching)
watch -n 3 'docker compose -f docker-compose.prod.yml ps'

# Expected output: all services show "healthy" or "running"
```

---

## 5. Run Database Migrations

Wait for PostgreSQL to be healthy before running migrations.

```bash
# Run Alembic migrations to bring schema to latest version
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify migration status
docker compose -f docker-compose.prod.yml exec backend alembic current
docker compose -f docker-compose.prod.yml exec backend alembic history --verbose
```

If this is a fresh deployment you should see all migrations applied to `head`.

---

## 6. Seed Superadmin

The seeding script creates the first tenant and superadmin user using values from `.env`.

```bash
# Run the seed script inside the backend container
docker compose -f docker-compose.prod.yml exec backend python -m scripts.seed_superadmin

# Expected output:
# [+] Creating default tenant: Your Company
# [+] Creating superadmin: admin@your-domain.com
# [+] Done. Login at https://your-domain.com with the configured credentials.
```

> **Important:** Change the superadmin password immediately after first login.

---

## 7. Nginx Reverse Proxy Configuration

### 7.1 Create Nginx Config File

```bash
sudo vim /etc/nginx/sites-available/ai-hrms
```

Paste the following configuration (replace `your-domain.com`):

```nginx
# ── Upstream Definitions ──────────────────────────────────────────────────────
upstream hrms_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream hrms_frontend {
    server 127.0.0.1:3000;
    keepalive 16;
}

# ── HTTP → HTTPS Redirect ─────────────────────────────────────────────────────
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com api.your-domain.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# ── Frontend (Next.js) ────────────────────────────────────────────────────────
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 256;

    client_max_body_size 50M;

    location / {
        proxy_pass http://hrms_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    # Static assets cache
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://hrms_frontend;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}

# ── Backend API ───────────────────────────────────────────────────────────────
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    client_max_body_size 50M;

    # WebSocket support (attendance + notifications)
    location /ws/ {
        proxy_pass http://hrms_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }

    location / {
        proxy_pass http://hrms_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }
}
```

### 7.2 Enable the Site

```bash
sudo ln -s /etc/nginx/sites-available/ai-hrms /etc/nginx/sites-enabled/ai-hrms
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## 8. SSL with Let's Encrypt (Certbot)

### 8.1 Obtain SSL Certificates

```bash
# Create certbot webroot directory
sudo mkdir -p /var/www/certbot

# Obtain certificates (ensure DNS A records for both domains point to this server)
sudo certbot --nginx -d your-domain.com -d api.your-domain.com \
  --non-interactive --agree-tos --email admin@your-domain.com \
  --redirect

# Verify certificates
sudo certbot certificates
```

### 8.2 Auto-Renewal

Certbot installs a systemd timer by default. Verify it is active:

```bash
sudo systemctl status certbot.timer
sudo systemctl enable certbot.timer

# Test renewal dry-run
sudo certbot renew --dry-run
```

### 8.3 Final Nginx Reload After Certbot

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 9. Systemd Auto-Restart Service

Create a systemd service so Docker Compose starts automatically on server reboot.

### 9.1 Create Service File

```bash
sudo vim /etc/systemd/system/ai-hrms.service
```

Paste:

```ini
[Unit]
Description=AI-HRMS Production Application
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ai-hrms
EnvironmentFile=/opt/ai-hrms/.env

ExecStart=/usr/local/bin/docker-compose -f /opt/ai-hrms/docker-compose.prod.yml up -d --remove-orphans
ExecStop=/usr/local/bin/docker-compose -f /opt/ai-hrms/docker-compose.prod.yml down
ExecReload=/usr/local/bin/docker-compose -f /opt/ai-hrms/docker-compose.prod.yml pull && \
           /usr/local/bin/docker-compose -f /opt/ai-hrms/docker-compose.prod.yml up -d --remove-orphans

Restart=on-failure
RestartSec=10s
TimeoutStartSec=300
TimeoutStopSec=120

StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-hrms

[Install]
WantedBy=multi-user.target
```

### 9.2 Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-hrms.service
sudo systemctl start ai-hrms.service
sudo systemctl status ai-hrms.service
```

---

## 10. PostgreSQL Backup Script

### 10.1 Create Backup Script

```bash
sudo mkdir -p /opt/backups/ai-hrms
sudo vim /opt/ai-hrms/scripts/backup.sh
```

Paste:

```bash
#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# AI-HRMS PostgreSQL Backup Script
# Schedule with cron: 0 2 * * * /opt/ai-hrms/scripts/backup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Load environment variables
source /opt/ai-hrms/.env

BACKUP_DIR="/opt/backups/ai-hrms"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/hrms_db_${DATE}.sql.gz"
RETENTION_DAYS=30
LOG_FILE="${BACKUP_DIR}/backup.log"

mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup: ${BACKUP_FILE}" | tee -a "${LOG_FILE}"

# Dump the database and compress
docker compose -f /opt/ai-hrms/docker-compose.prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup succeeded: ${BACKUP_FILE} (${SIZE})" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup FAILED!" | tee -a "${LOG_FILE}"
    exit 1
fi

# Remove backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -name "hrms_db_*.sql.gz" -mtime +${RETENTION_DAYS} -exec rm -f {} \; -print | tee -a "${LOG_FILE}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup rotation complete. Keeping last ${RETENTION_DAYS} days." | tee -a "${LOG_FILE}"

# Optional: Upload to S3
# aws s3 cp "${BACKUP_FILE}" "s3://your-backup-bucket/ai-hrms/" --storage-class STANDARD_IA
```

### 10.2 Make Executable and Schedule

```bash
sudo chmod +x /opt/ai-hrms/scripts/backup.sh

# Add to crontab (runs daily at 2:00 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/ai-hrms/scripts/backup.sh >> /opt/backups/ai-hrms/backup.log 2>&1") | crontab -

# Verify cron entry
crontab -l
```

### 10.3 Manual Backup

```bash
/opt/ai-hrms/scripts/backup.sh
ls -lh /opt/backups/ai-hrms/
```

### 10.4 Restore from Backup

```bash
BACKUP_FILE="/opt/backups/ai-hrms/hrms_db_YYYYMMDD_HHMMSS.sql.gz"

# Stop backend to prevent writes during restore
docker compose -f /opt/ai-hrms/docker-compose.prod.yml stop backend celery-worker celery-beat

# Restore
gunzip -c "${BACKUP_FILE}" | docker compose -f /opt/ai-hrms/docker-compose.prod.yml exec -T postgres \
  psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"

# Restart services
docker compose -f /opt/ai-hrms/docker-compose.prod.yml start backend celery-worker celery-beat
```

---

## 11. Monitoring

### 11.1 View Live Container Stats

```bash
# Real-time CPU and memory usage for all containers
docker stats

# For specific containers
docker stats hrms_backend hrms_postgres hrms_redis
```

### 11.2 View Logs

```bash
cd /opt/ai-hrms

# All service logs (last 100 lines, follow)
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Single service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Filter errors only
docker compose -f docker-compose.prod.yml logs backend 2>&1 | grep -i "error\|exception"
```

### 11.3 Health Check Endpoints

```bash
# Backend health
curl -f https://api.your-domain.com/health

# Detailed health (DB + Redis connectivity)
curl -f https://api.your-domain.com/health/detailed
```

### 11.4 Disk Usage

```bash
# Docker volumes
docker system df -v

# Overall disk
df -h /

# Backup directory
du -sh /opt/backups/ai-hrms/
```

### 11.5 Optional: Prometheus + Grafana

The backend exposes metrics at `/metrics` (Prometheus format). To add monitoring:

```bash
# Add to docker-compose.prod.yml or run separately
docker run -d --name prometheus -p 9090:9090 \
  -v /opt/ai-hrms/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

docker run -d --name grafana -p 3001:3000 grafana/grafana
```

---

## 12. Rollback Procedure

### 12.1 Rollback to Previous Docker Image

```bash
cd /opt/ai-hrms

# View available image tags
docker images | grep hrms

# Edit docker-compose.prod.yml to pin to previous image tag
# e.g., change image: hrms-backend:1.3.0 → hrms-backend:1.2.5

# Pull and redeploy
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

### 12.2 Rollback Database Migration

```bash
# View current migration head
docker compose -f docker-compose.prod.yml exec backend alembic current

# Roll back one migration
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# Roll back to a specific revision
docker compose -f docker-compose.prod.yml exec backend alembic downgrade <revision_id>
```

### 12.3 Rollback via Git

```bash
cd /opt/ai-hrms

# View recent tags/commits
git log --oneline -10

# Checkout previous release tag
git checkout v1.2.5

# Rebuild and restart
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Run migrations for the checked-out version
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 12.4 Emergency Database Restore

If a migration caused data corruption, restore from the latest backup:

```bash
# 1. Stop application
docker compose -f docker-compose.prod.yml stop backend celery-worker celery-beat

# 2. Drop and recreate database
docker compose -f docker-compose.prod.yml exec postgres psql -U hrms_user -c "DROP DATABASE hrms_db;"
docker compose -f docker-compose.prod.yml exec postgres psql -U hrms_user -c "CREATE DATABASE hrms_db;"

# 3. Restore latest backup
LATEST_BACKUP=$(ls -t /opt/backups/ai-hrms/hrms_db_*.sql.gz | head -1)
gunzip -c "${LATEST_BACKUP}" | docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U hrms_user hrms_db

# 4. Restart
docker compose -f docker-compose.prod.yml start backend celery-worker celery-beat
```

---

## Quick Reference

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Stop all services
docker compose -f docker-compose.prod.yml down

# Restart a single service
docker compose -f docker-compose.prod.yml restart backend

# Execute a command inside a container
docker compose -f docker-compose.prod.yml exec backend bash

# View resource usage
docker stats

# Run manual backup
/opt/ai-hrms/scripts/backup.sh

# Check systemd service
sudo systemctl status ai-hrms.service
```
