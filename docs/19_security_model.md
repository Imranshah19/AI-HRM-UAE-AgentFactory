# SECTION 10 — SECURITY MODEL

## 10.1 HRMS-Specific Threat Model (Top 10)

| # | Threat | Attack Vector | HRMS-Specific Risk | Mitigation |
|---|---|---|---|---|
| T1 | **Broken Access Control / IDOR** | Attacker changes `employee_id` in URL to access other employee's payslip | Any employee can view any other's salary, CNIC, bank details | UUID PKs (non-guessable), RBAC on every endpoint, tenant_id validation, automated IDOR scanner in CI |
| T2 | **Tenant Data Leakage** | Missing tenant_id filter in query returns rows from another organization | Competitor sees your entire employee list and payroll | PostgreSQL RLS, tenant_id on every WHERE, RLS policy unit-tested on every query |
| T3 | **Credential Stuffing / Brute Force** | Attacker tests 1M username/password combos from leaked DB | Mass account compromise, data exfiltration | Login rate limit (10/min/IP), account lockout after 5 failures, TOTP MFA mandatory for HR/Admin, CAPTCHA on login |
| T4 | **JWT Token Theft** | XSS extracts access token from localStorage | Attacker impersonates HR Manager for 15 minutes | Tokens stored in httpOnly cookies (not localStorage), strict CSP headers block inline scripts, short 15-min TTL |
| T5 | **Insecure File Upload (CV/Doc upload)** | Attacker uploads PHP webshell as "CV.pdf" | Remote code execution on server | File type whitelist (PDF, DOCX, JPEG only), magic byte validation (not extension), upload to S3 directly (never executed), ClamAV scan on upload |
| T6 | **SQL Injection via Report Builder** | Custom report builder allows free-form field names — attacker injects `; DROP TABLE employees;--` | Data destruction, full DB dump | Whitelist-only field names, parameterized queries enforced by SQLAlchemy ORM, never raw SQL with user input, NLQ validator in AI analytics module |
| T7 | **Mass Assignment (PATCH endpoint)** | Attacker sends `{"role": "super_admin", "salary": 999999}` in employee update | Privilege escalation, salary fraud | Pydantic schema explicitly declares allowed fields, role and salary cannot be updated via employee PATCH (separate endpoints with separate RBAC) |
| T8 | **Payroll Fraud via Approval Bypass** | Insider bypasses approval stages by directly calling approve API with wrong role | Unauthorized payroll run, fraudulent payments | Approval stage validation in service layer (not just RBAC), database-level state machine, 4-eyes principle (HR + Finance + CEO), full audit trail with IP logging |
| T9 | **Sensitive Data Exposure in Logs** | Logging middleware accidentally logs request body containing salary or CNIC | PII in log aggregation system (ELK) | Request body logging DISABLED for sensitive endpoints (/payroll, /compensation), salary/CNIC fields masked in all logs, Kibana access restricted to Security team |
| T10 | **Supply Chain Attack (dependency)** | Malicious package injected into requirements.txt (similar to event-stream attack) | Full server compromise | pip-audit and safety in every CI run, hash-pinned requirements (pip-compile), Dependabot automated PRs for CVEs, Trivy image scan in CI pipeline |

---

## 10.2 Encrypted Fields List (AES-256 Column-Level)

All encryption/decryption handled at **application layer** (Python) before DB write / after DB read.
Database stores only ciphertext — even a DB dump reveals no plaintext.

```python
# core/encryption.py
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os
import json

class FieldEncryptor:
    """
    AES-256-GCM field-level encryption.
    Key rotation supported via MultiFernet (old keys kept for decryption).
    """

    def __init__(self):
        # Primary key for encryption, old keys for decryption during rotation
        primary_key = os.environ["FIELD_ENCRYPTION_KEY_PRIMARY"].encode()
        old_keys = os.environ.get("FIELD_ENCRYPTION_KEY_SECONDARY", "").split(",")

        keys = [Fernet(primary_key)]
        for k in old_keys:
            if k.strip():
                keys.append(Fernet(k.strip().encode()))

        self._fernet = MultiFernet(keys)

    def encrypt(self, value: str | None) -> str | None:
        """Encrypt a string value. Returns base64 ciphertext."""
        if value is None:
            return None
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, ciphertext: str | None) -> str | None:
        """Decrypt a stored ciphertext. Returns plaintext string."""
        if ciphertext is None:
            return None
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def encrypt_json(self, data: dict | list) -> str | None:
        """Encrypt a dict/list as JSON string."""
        if data is None:
            return None
        return self.encrypt(json.dumps(data))

    def decrypt_json(self, ciphertext: str | None) -> dict | list | None:
        plaintext = self.decrypt(ciphertext)
        return json.loads(plaintext) if plaintext else None


# Global instance — initialized once at startup
encryptor = FieldEncryptor()


# SQLAlchemy TypeDecorator for transparent encryption
from sqlalchemy import TypeDecorator, String

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy column type that automatically encrypts on write
    and decrypts on read.
    Usage: Column(EncryptedString())
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Called when writing to DB."""
        if value is None:
            return None
        return encryptor.encrypt(str(value))

    def process_result_value(self, value, dialect):
        """Called when reading from DB."""
        if value is None:
            return None
        return encryptor.decrypt(value)
```

### Encrypted Fields Registry

| Table | Column | Sensitivity Level | Encryption |
|---|---|---|---|
| employees | `cnic_nid_encrypted` | Critical | AES-256-GCM |
| employee_compensation | `basic_salary_encrypted` | High | AES-256-GCM |
| employee_compensation | `hra_encrypted`, all allowances | High | AES-256-GCM |
| employee_compensation | `bank_account_number_encrypted` | Critical | AES-256-GCM |
| employee_compensation | `bank_iban_encrypted` | Critical | AES-256-GCM |
| payroll_records | `earnings` JSONB | High | Application-layer JSON encryption |
| payroll_records | `deductions` JSONB | High | Application-layer JSON encryption |
| users | `totp_secret` | Critical | AES-256-GCM |
| users | `backup_codes` (hashed) | High | bcrypt hash (not reversible) |
| employee_documents | S3 objects | High | S3 SSE-KMS (AWS managed key) |

---

## 10.3 Audit Log Specification

```sql
-- Full schema in Section 2 (audit_logs table)
-- Key immutability guarantees:

-- 1. PostgreSQL RULES prevent modification:
CREATE RULE no_update_audit AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE no_delete_audit AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- 2. DB user permissions (hrms_app role):
REVOKE UPDATE, DELETE ON audit_logs FROM hrms_app;
GRANT INSERT, SELECT ON audit_logs TO hrms_app;

-- 3. Table partitioning for performance (monthly partitions):
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- Created automatically via pg_partman extension

-- 4. After 30 days: export to S3 and optionally drop partition from hot DB
--    Retention: 7 years in S3 Glacier
```

### Audit Log Sample Entries
```python
# What gets logged and when

# Employee salary update
{
    "action": "employee.compensation.update",
    "resource_type": "employee_compensation",
    "resource_id": "emp_comp_uuid",
    "resource_label": "Muhammad Ahmed — Compensation",
    "old_values": {"basic_salary": "[ENCRYPTED]", "effective_date": "2023-01-01"},
    "new_values": {"basic_salary": "[ENCRYPTED]", "effective_date": "2024-01-01"},
    "diff": {"effective_date": {"old": "2023-01-01", "new": "2024-01-01"}},
    "actor_email": "hr@company.com",
    "actor_ip": "10.0.1.52",
    "severity": "critical"
}

# Payroll approval
{
    "action": "payroll.run.approved",
    "resource_type": "payroll_runs",
    "resource_id": "run_uuid",
    "resource_label": "PR-2024-01 — January 2024",
    "new_values": {"status": "pending_finance", "hr_approved_by": "hr_uuid"},
    "actor_email": "hr@company.com",
    "severity": "critical"
}

# Login (security event)
{
    "action": "auth.login.success",
    "resource_type": "users",
    "resource_id": "user_uuid",
    "resource_label": "hr@company.com",
    "new_values": {"login_at": "2024-01-15T09:12:00Z", "mfa_used": true},
    "actor_ip": "203.0.113.45",
    "actor_user_agent": "Mozilla/5.0...",
    "severity": "info"
}

# Failed login (security event)
{
    "action": "auth.login.failed",
    "resource_type": "users",
    "resource_label": "unknown@company.com",
    "new_values": {"reason": "invalid_password", "attempt_count": 3},
    "actor_ip": "198.51.100.23",
    "severity": "warning"
}

# AI override
{
    "action": "ai.decision.overridden",
    "resource_type": "job_applications",
    "resource_id": "app_uuid",
    "old_values": {"ai_recommendation": "reject", "ai_score": 42},
    "new_values": {"hr_decision": "shortlist", "override_reason": "Strong referral"},
    "is_ai_action": false,
    "ai_decision_id": "ai_dec_uuid",
    "severity": "warning"
}
```

---

## 10.4 Security Headers (Nginx Configuration)

```nginx
# docker/nginx/production.conf
server {
    listen 443 ssl http2;
    server_name api.hrms.company.com;

    ssl_certificate     /etc/letsencrypt/live/hrms.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hrms.company.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;

    # HSTS — force HTTPS for 2 years, include subdomains
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Prevent clickjacking
    add_header X-Frame-Options "DENY" always;

    # Prevent MIME sniffing
    add_header X-Content-Type-Options "nosniff" always;

    # Content Security Policy (restrictive for API)
    add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none';" always;

    # Remove server banner
    server_tokens off;
    more_clear_headers Server;

    # Referrer policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Permissions policy
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(self)" always;

    # CORS (handled in FastAPI, but Nginx can enforce origin)
    # Only allow company-owned origins
    set $cors_origin "";
    if ($http_origin ~* "^https://(app\.hrms\.company\.com|admin\.hrms\.company\.com)$") {
        set $cors_origin $http_origin;
    }

    location /api/ {
        proxy_pass http://hrms-api-svc:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Timeouts
        proxy_read_timeout 300s;    # payroll runs take time
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;

        # Body size limit (for file uploads)
        client_max_body_size 50M;
    }

    location /ws/ {
        proxy_pass http://hrms-api-svc:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;   # keep WS alive for 1h
    }

    # Block common attack paths
    location ~* \.(git|env|sql|bak|log)$ {
        deny all;
        return 404;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

---

## 10.5 OWASP Top 10 → HRMS Attack Surface Map

```python
# security/owasp_checklist.py

OWASP_MITIGATIONS = {

    "A01:2021 Broken Access Control": {
        "hrms_surfaces": [
            "GET /employees/{id} — employee viewing another's payslip",
            "GET /payroll/{id}/bank-file — non-Finance downloading bank file",
            "PATCH /employees/{id}/compensation — employee changing own salary",
        ],
        "mitigations": [
            "RBAC decorator on every endpoint: @require_permission('resource:action')",
            "UUID PKs prevent enumeration",
            "Tenant isolation: tenant_id check on every DB query",
            "Field-level masking: salary hidden from non-Finance roles",
            "Automated IDOR tests in CI: test_employee_cannot_access_other_employee_data()",
        ],
        "test_command": "pytest tests/security/test_idor.py -v",
    },

    "A02:2021 Cryptographic Failures": {
        "hrms_surfaces": [
            "CNIC stored in database",
            "Bank account numbers stored",
            "Payslip PDFs in S3",
            "JWT tokens in browser",
        ],
        "mitigations": [
            "AES-256-GCM field-level encryption for CNIC, bank details, salary",
            "S3 SSE-KMS for all uploaded documents",
            "JWT in httpOnly, Secure, SameSite=Strict cookies (not localStorage)",
            "TLS 1.3 minimum, TLS 1.0/1.1 disabled",
            "Key rotation supported via MultiFernet",
        ],
    },

    "A03:2021 Injection": {
        "hrms_surfaces": [
            "Custom report builder (field names, filter values)",
            "Employee search (?search=...)",
            "AI NLQ analytics (generates SQL from user query)",
            "Notification template variables",
        ],
        "mitigations": [
            "SQLAlchemy ORM: all queries parameterized — never raw f-string SQL",
            "Report builder: whitelist-only field names from predefined enum",
            "NLQ analytics: SQL validator strips all non-SELECT operations",
            "Elasticsearch queries: structured DSL objects, not string concatenation",
            "Jinja2 with autoescape=True for notification templates",
            "OWASP ZAP scan in CI pipeline",
        ],
    },

    "A04:2021 Insecure Design": {
        "hrms_surfaces": [
            "Payroll approval flow could be bypassed if stage not enforced in DB",
            "Leave balance could go negative if concurrent requests processed",
        ],
        "mitigations": [
            "Payroll approval: DB-level CHECK constraint on status transitions",
            "Optimistic locking on leave_balances table (version column)",
            "Pessimistic lock on payroll_run creation: SELECT FOR UPDATE",
            "Threat model reviewed quarterly by security team",
        ],
    },

    "A05:2021 Security Misconfiguration": {
        "hrms_surfaces": [
            "DEBUG=True left on in production",
            "Default admin credentials not changed",
            "Elasticsearch open to internet",
            "S3 bucket public by default",
        ],
        "mitigations": [
            "DEBUG forced to False if ENVIRONMENT=production (startup validation)",
            "No default credentials — admin creates first user via seed script with random password",
            "Elasticsearch inside VPC — no public endpoint",
            "S3 bucket ACL = private, public-read only for specific /public/ prefix",
            "Automated config scan: detect-secrets in pre-commit hooks",
        ],
    },

    "A06:2021 Vulnerable Components": {
        "hrms_surfaces": [
            "Outdated FastAPI, Celery, pdfplumber with known CVEs",
            "Node.js frontend with vulnerable npm packages",
        ],
        "mitigations": [
            "pip-audit and safety run in every CI pipeline",
            "npm audit in frontend CI",
            "Dependabot auto-PRs for security patches",
            "Trivy image scan on every Docker build",
            "requirements.txt with hash-pinning via pip-compile",
        ],
    },

    "A07:2021 Auth Failures": {
        "hrms_surfaces": [
            "Login endpoint brute force",
            "JWT not invalidated after password change",
            "Weak password accepted",
        ],
        "mitigations": [
            "Login: 10 req/min per IP, account lock after 5 failures",
            "Password change: revoke all existing refresh tokens immediately",
            "TOTP MFA mandatory for HR, Finance, Admin roles",
            "Password policy: min 12 chars, must include upper, lower, digit, special",
            "Session management: Redis-based token revocation list",
        ],
    },

    "A08:2021 Integrity Failures": {
        "hrms_surfaces": [
            "CI/CD pipeline poisoning",
            "Malicious pip package update",
            "Docker image tampered in registry",
        ],
        "mitigations": [
            "GitHub branch protection: PR reviews required for main branch",
            "Signed commits required for releases",
            "Docker image digest pinning in K8s manifests",
            "GitHub Actions: OIDC authentication to AWS (no static credentials)",
        ],
    },

    "A09:2021 Logging & Monitoring Failures": {
        "hrms_surfaces": [
            "Failed login attempts not alerted on",
            "Bulk data export not monitored",
            "After-hours payroll access undetected",
        ],
        "mitigations": [
            "CloudWatch alert: >10 failed logins from same IP in 5 minutes",
            "Audit log alert: bulk export >500 rows triggers Slack/PagerDuty notification",
            "After-hours access alert: payroll actions outside 8AM-7PM business hours",
            "Sentry error tracking with PagerDuty integration",
            "Weekly security report: unusual access patterns summary to CISO",
        ],
    },

    "A10:2021 SSRF": {
        "hrms_surfaces": [
            "Webhook configuration (tenant can set webhook URLs)",
            "External job board API calls use user-provided URLs",
            "Document download from external URLs",
        ],
        "mitigations": [
            "Webhook URLs: validated against allowlist of known safe domains",
            "Outbound HTTP: blocked to 169.254.169.254 (EC2 metadata), 10.x, 172.x",
            "External URL fetch: runs through SSRF-safe proxy with IP blocklist",
            "DNS rebinding protection: resolved IP re-checked against blocklist",
        ],
    },
}
```

---

## 10.6 Incident Response Plan

```
HRMS SECURITY INCIDENT RESPONSE PLAN
Version: 1.0 | Owner: Platform Security Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1: DETECT (0-15 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources:
  - Sentry error alerts → PagerDuty → On-call engineer
  - CloudWatch anomaly alert (login spikes, bulk exports)
  - User report via security@company.com

Immediate actions:
  [ ] Confirm it is a true positive (not false alarm)
  [ ] Classify severity:
      P1 (Critical): Data breach, production DB compromised, payroll tampered
      P2 (High):     Unauthorized access to sensitive data (1 employee)
      P3 (Medium):   Brute force attack in progress, unusual access pattern
      P4 (Low):      Vulnerability discovered (not yet exploited)
  [ ] Alert security lead + CTO for P1/P2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2: CONTAIN (15-60 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For compromised account:
  [ ] Immediately revoke all sessions:
      Redis: KEYS "session:user_id:*" | XARGS DEL
      DB: UPDATE user_sessions SET is_revoked=TRUE WHERE user_id=...
  [ ] Disable user account: UPDATE users SET is_active=FALSE WHERE id=...
  [ ] Block IP in WAF: aws wafv2 update-ip-set --...

For suspected data breach:
  [ ] Enable maintenance mode (optional — for P1 only)
  [ ] Snapshot DB immediately: aws rds create-db-snapshot --...
  [ ] Preserve audit logs: export affected time range to S3 immediately
  [ ] DO NOT delete any logs (evidence)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3: ERADICATE (1-4 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ ] Root cause analysis using audit logs + Kibana
  [ ] Identify all affected data (which employees, what fields)
  [ ] Patch the vulnerability (hotfix branch → PR → emergency deploy)
  [ ] Rotate compromised credentials: JWT_SECRET_KEY, DB password, S3 keys
  [ ] Scan for backdoors: run Trivy on all running containers
  [ ] Force re-authentication for all affected users

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4: RECOVER (4-24 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ ] Verify fix is complete (re-run security scan)
  [ ] Restore service from clean snapshot if DB was corrupted
  [ ] Monitor for 24h: enhanced logging, WAF alert thresholds reduced
  [ ] Notify affected employees (if PII was accessed)
  [ ] GDPR notification to DPA within 72 hours if personal data breached

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5: POST-INCIDENT REVIEW (within 5 days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ ] Write incident post-mortem (timeline, root cause, impact, fix)
  [ ] Update threat model with new attack vector
  [ ] Add regression test to CI for the vulnerability
  [ ] Review OWASP checklist for similar patterns
  [ ] Present findings to engineering team
```
