# SECTION 12 — DISASTER RECOVERY, LEGACY MIGRATION & COST OPTIMIZATION

## 12.1 Disaster Recovery Plan

### RPO & RTO Targets
| Scenario | RPO (Max Data Loss) | RTO (Recovery Time) | Strategy |
|---|---|---|---|
| Single app pod failure | 0 (stateless) | <30 seconds | K8s pod restart |
| DB primary failure | <5 minutes | <15 minutes | RDS Multi-AZ auto-failover |
| Redis cluster node failure | <1 minute (non-critical) | <5 minutes | ElastiCache auto-failover |
| Elasticsearch node failure | 0 (replicas) | <10 minutes | Replica promotion |
| Full availability zone failure | <5 minutes | <30 minutes | Multi-AZ auto-failover |
| Full region failure | <1 hour | <4 hours | Cross-region warm standby |
| Data corruption | <1 hour | <4 hours | S3 backup restore |

### Multi-Region Architecture
```
Primary Region (ap-south-1 — Mumbai):
  ├── RDS PostgreSQL (Multi-AZ: primary + synchronous standby)
  ├── ElastiCache Redis (Multi-AZ cluster)
  ├── OpenSearch (3-node cluster, cross-AZ)
  ├── S3 bucket (cross-region replication ENABLED)
  └── EKS cluster (3 worker nodes, 3 AZs)

Secondary Region (ap-southeast-1 — Singapore) — WARM STANDBY:
  ├── RDS PostgreSQL Read Replica (promoted on failover)
  ├── ElastiCache Redis (warm standby, not serving traffic)
  ├── S3 bucket (CRR destination)
  └── EKS cluster (minimal 1 node — scales up on failover)

Failover Trigger:
  ├── Route 53 health checks poll /api/v1/system/health every 30s
  ├── If 3 consecutive failures → DNS failover to secondary region
  └── CloudWatch alarm → SNS → PagerDuty → on-call engineer
```

### PostgreSQL Replication Setup
```bash
# Primary: postgresql.conf
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
synchronous_standby_names = 'standby01'  # sync for same-AZ standby
# Cross-region replica is asynchronous (latency constraint)

# Create replication slot (prevents WAL deletion until replica consumes)
SELECT pg_create_physical_replication_slot('replica_ap_southeast_1');

# Recovery target consistency level
synchronous_commit = 'remote_write'  # RPO ~0 for same-AZ, ~1min for cross-region
```

### DR Drill Runbook (Quarterly)

```
QUARTERLY DR DRILL PROCEDURE
Last Updated: 2024-01-01
Owner: Platform Engineering Team

PRE-DRILL (Day before):
  [ ] Notify all teams of planned drill window (2h maintenance)
  [ ] Verify backup integrity: test-restore last 3 daily backups
  [ ] Confirm secondary region resources are healthy
  [ ] Create pre-drill checkpoint in git: git tag dr-drill-$(date +%Y%m%d)
  [ ] Enable maintenance page on primary region

DRILL STEPS:
  Step 1: Simulate primary region failure
    [ ] Route53: change record health check threshold to force failover
    [ ] Verify DNS propagation (max 60s with 60s TTL)
    [ ] Start timer

  Step 2: Secondary region activation
    [ ] RDS: Promote read replica to primary
        aws rds promote-read-replica --db-instance-identifier hrms-pg-secondary
    [ ] Update DATABASE_URL secret in secondary region Vault/Secrets Manager
    [ ] EKS: Scale up secondary cluster (0 → 3 worker nodes)
        kubectl scale deployment hrms-api --replicas=3 -n production
    [ ] Verify pod startup: kubectl get pods -n production -w
    [ ] Run DB migration check: alembic current (should show latest revision)

  Step 3: Validation
    [ ] Smoke test: curl https://api.hrms.company.com/api/v1/system/health
    [ ] Login flow test (JWT + TOTP)
    [ ] Read attendance records (tests DB connectivity)
    [ ] Create test employee (tests DB write)
    [ ] Verify file upload to S3 (tests cross-region CRR)
    [ ] Record actual RTO: _____ minutes (target: <4 hours, pass: <4h)
    [ ] Verify data integrity: compare row counts with pre-drill snapshot

  Step 4: Failback
    [ ] Re-enable primary region
    [ ] Sync delta changes from secondary back to primary (pg_logical)
    [ ] Switch DNS back to primary
    [ ] Drain secondary region traffic
    [ ] Scale down secondary cluster

POST-DRILL:
  [ ] Document actual RPO and RTO achieved
  [ ] Log incidents or gaps found
  [ ] Update runbook with lessons learned
  [ ] Create Jira tickets for any gaps
```

---

## 12.2 Legacy Data Migration ETL Plan

### Pipeline Architecture (Apache Airflow)

```python
# dags/legacy_migration_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine

default_args = {
    "owner": "platform_team",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["platform@company.com"],
}

with DAG(
    "legacy_hrms_migration",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=["migration", "etl"],
) as dag:

    # Phase 1: Extract
    extract_employees = PythonOperator(
        task_id="extract_employees_from_legacy",
        python_callable=extract_legacy_employees,
    )

    # Phase 2: Validate
    validate_data = PythonOperator(
        task_id="validate_extracted_data",
        python_callable=validate_and_report,
    )

    # Phase 3: Transform
    transform_data = PythonOperator(
        task_id="transform_to_new_schema",
        python_callable=transform_employees,
    )

    # Phase 4: Load (dry run)
    dry_run_load = PythonOperator(
        task_id="dry_run_load_to_staging",
        python_callable=load_to_staging,
        op_kwargs={"dry_run": True},
    )

    # Phase 5: Load (production)
    production_load = PythonOperator(
        task_id="load_to_production",
        python_callable=load_to_production,
    )

    # Phase 6: Post-migration audit
    audit_report = PythonOperator(
        task_id="generate_migration_audit_report",
        python_callable=generate_audit_report,
    )

    notify_complete = EmailOperator(
        task_id="notify_migration_complete",
        to=["hr_team@company.com", "platform@company.com"],
        subject="HRMS Migration Complete — Audit Report Attached",
        html_content="{{ task_instance.xcom_pull('generate_migration_audit_report') }}",
    )

    (extract_employees >> validate_data >> transform_data
     >> dry_run_load >> production_load >> audit_report >> notify_complete)


def extract_legacy_employees(**context) -> str:
    """Extract employees from legacy system (CSV or direct DB)."""
    legacy_engine = create_engine(os.environ["LEGACY_DB_URL"])

    df = pd.read_sql("""
        SELECT
            emp_id, emp_name, emp_dept, emp_designation, emp_joining,
            emp_dob, emp_cnic, emp_email, emp_phone, emp_salary,
            emp_bank_account, emp_status
        FROM employees
        WHERE emp_status != 'deleted'
    """, legacy_engine)

    output_path = f"/tmp/legacy_employees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_path, index=False)
    context["ti"].xcom_push(key="employee_csv", value=output_path)
    context["ti"].xcom_push(key="row_count", value=len(df))

    return output_path


def validate_and_report(**context) -> dict:
    """Validate extracted data before transformation."""
    csv_path = context["ti"].xcom_pull(key="employee_csv", task_ids="extract_employees_from_legacy")
    df = pd.read_csv(csv_path)

    errors = []
    warnings = []

    # Mandatory field checks
    mandatory_fields = ["emp_id", "emp_name", "emp_email", "emp_joining"]
    for field in mandatory_fields:
        null_count = df[field].isna().sum()
        if null_count > 0:
            errors.append(f"MANDATORY_NULL: {field} is null in {null_count} rows")

    # Format validation
    cnic_invalid = df["emp_cnic"].apply(
        lambda x: not bool(re.match(r'^\d{5}-\d{7}-\d$', str(x))) if pd.notna(x) else False
    ).sum()
    if cnic_invalid > 0:
        warnings.append(f"CNIC_FORMAT: {cnic_invalid} rows have invalid CNIC format")

    # Email uniqueness
    duplicate_emails = df["emp_email"].duplicated().sum()
    if duplicate_emails > 0:
        errors.append(f"DUPLICATE_EMAIL: {duplicate_emails} duplicate email addresses")

    # Salary sanity check
    zero_salary = (df["emp_salary"] <= 0).sum()
    if zero_salary > 0:
        warnings.append(f"ZERO_SALARY: {zero_salary} employees with zero salary")

    report = {
        "total_rows": len(df),
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "validation_passed": len(errors) == 0,
    }

    if errors:
        raise ValueError(f"Validation failed with {len(errors)} errors: {errors}")

    return report


def transform_employees(**context) -> str:
    """Transform legacy schema to new HRMS schema."""
    csv_path = context["ti"].xcom_pull(key="employee_csv", task_ids="extract_employees_from_legacy")
    df = pd.read_csv(csv_path)

    # Field mapping: legacy → new
    FIELD_MAP = {
        "emp_id": "legacy_id",
        "emp_name": "_full_name",         # will split into first/last
        "emp_dept": "department_code",
        "emp_designation": "designation",
        "emp_joining": "joining_date",
        "emp_dob": "date_of_birth",
        "emp_cnic": "cnic_nid",
        "emp_email": "personal_email",
        "emp_phone": "phone_primary",
        "emp_salary": "basic_salary",
        "emp_bank_account": "bank_account_number",
        "emp_status": "_status_map",
    }

    df = df.rename(columns=FIELD_MAP)

    # Split full_name into first_name / last_name
    df["first_name"] = df["_full_name"].apply(lambda x: str(x).split()[0] if pd.notna(x) else "")
    df["last_name"] = df["_full_name"].apply(
        lambda x: " ".join(str(x).split()[1:]) if pd.notna(x) else ""
    )

    # Normalize status
    STATUS_MAP = {
        "ACTIVE": "active", "RESIGNED": "offboarding", "TERMINATED": "offboarding",
        "PROBATION": "probation", "INACTIVE": "suspended",
    }
    df["lifecycle_status"] = df["_status_map"].map(STATUS_MAP).fillna("active")

    # Format dates
    df["joining_date"] = pd.to_datetime(df["joining_date"], dayfirst=True, errors="coerce")
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], dayfirst=True, errors="coerce")

    # Generate employee_number if not present
    df["employee_number"] = df.apply(
        lambda row: row.get("emp_id") or f"EMP-{str(row.name + 1).zfill(4)}",
        axis=1,
    )

    output_path = csv_path.replace("legacy_employees", "transformed_employees")
    df.to_csv(output_path, index=False)
    return output_path
```

### Cutover Plan

```
MIGRATION CUTOVER PLAN
Mode: Department-by-Department (Phased)
Reason: Reduces risk; allows validation per department before proceeding

WEEK 1: HR & Finance departments (smallest, best for testing)
  Day 1: Migrate HR + Finance employees
  Day 2-3: Parallel run validation (old system + new system simultaneously)
  Day 4: Sign-off from HR Director
  Day 5: Cut HR + Finance to new system only

WEEK 2: IT, Engineering, Operations
WEEK 3: Sales, Marketing, Customer Service
WEEK 4: Remaining + cleanup

ROLLBACK STRATEGY:
  Before each phase:
    pg_dump hrms_production > backup_pre_phase_{n}.dump
  If rollback needed:
    1. Stop new system API pods
    2. Restore: pg_restore -d hrms_production backup_pre_phase_{n}.dump
    3. Re-enable old system
    4. Notify affected departments
    5. Investigate and fix migration issue before retry

PARALLEL RUN:
  During parallel period:
  - Both systems receive all changes (sync via webhook listener on old system)
  - Daily comparison report: row count diff, field value diff
  - Max 3 days parallel per department
  - Requires 0 data discrepancies before sign-off
```

---

## 12.3 Cloud Cost Optimization

### Kubernetes HPA Configuration
```yaml
# k8s/hpa-api.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hrms-api-hpa
  namespace: production
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
        averageUtilization: 65   # scale up when CPU > 65%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"      # scale when >100 req/s per pod
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300    # wait 5min before scale-down
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60               # remove max 2 pods per minute
    scaleUp:
      stabilizationWindowSeconds: 30     # scale up after 30s of high load
      policies:
      - type: Pods
        value: 4
        periodSeconds: 60               # add max 4 pods per minute
```

### S3 Lifecycle Policy
```json
{
  "Rules": [
    {
      "ID": "payslip-lifecycle",
      "Status": "Enabled",
      "Filter": {"Prefix": "payslips/"},
      "Transitions": [
        {"Days": 365,  "StorageClass": "STANDARD_IA"},
        {"Days": 2555, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 3650}
    },
    {
      "ID": "temp-uploads-cleanup",
      "Status": "Enabled",
      "Filter": {"Prefix": "temp/"},
      "Expiration": {"Days": 1}
    },
    {
      "ID": "audit-exports-archive",
      "Status": "Enabled",
      "Filter": {"Prefix": "audit-exports/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "GLACIER_IR"}
      ],
      "Expiration": {"Days": 2555}
    }
  ]
}
```

### Cost Dashboard (Grafana Query)
```promql
# Monthly spend per service (requires AWS Cost Explorer metric exporter)
sum by (service) (
  aws_billing_estimated_charges{
    currency="USD",
    job="aws-cost-exporter"
  }
)

# DB connection count (PgBouncer reduces RDS instance requirement)
pgbouncer_pools_cl_active / pgbouncer_config_max_client_conn * 100

# Redis memory utilization
redis_memory_used_bytes / redis_memory_max_bytes * 100
```

# SECTION 8 — TESTING STRATEGY

## GitHub Actions CI Pipeline
```yaml
# .github/workflows/ci.yml
name: HRMS CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"
  POSTGRES_DB: hrms_test
  POSTGRES_USER: hrms_test
  POSTGRES_PASSWORD: test_password

jobs:
  # ── Backend Tests ──────────────────────────────────────────────────
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: ${{ env.POSTGRES_DB }}
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Run migrations
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql://hrms_test:test_password@localhost:5432/hrms_test

      - name: Run unit tests with coverage
        run: |
          pytest tests/unit \
            --cov=app \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80 \
            -v
        env:
          DATABASE_URL: postgresql://hrms_test:test_password@localhost:5432/hrms_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test_secret_key_minimum_32_chars_long
          ENVIRONMENT: test

      - name: Run integration tests
        run: |
          pytest tests/integration \
            -v \
            --timeout=60
        env:
          DATABASE_URL: postgresql://hrms_test:test_password@localhost:5432/hrms_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test_secret_key_minimum_32_chars_long

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  # ── Linting & Type Check ───────────────────────────────────────────
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install ruff mypy
      - run: ruff check app/ tests/
      - run: mypy app/ --ignore-missing-imports

  # ── Security Scan ──────────────────────────────────────────────────
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install safety pip-audit
      - name: Check for vulnerable dependencies
        run: |
          pip install -r requirements.txt
          pip-audit --strict
      - name: OWASP ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: "http://localhost:8000"  # started in docker-compose
          rules_file_name: ".zap/rules.tsv"
          cmd_options: "-a"

  # ── Frontend Tests ─────────────────────────────────────────────────
  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm run type-check
        working-directory: frontend
      - run: npm run test
        working-directory: frontend
      - name: Build Next.js
        run: npm run build
        working-directory: frontend

  # ── Docker Build ───────────────────────────────────────────────────
  docker-build:
    needs: [backend-test, lint, frontend-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build API image
        run: docker build -f docker/Dockerfile.api -t hrms-api:${{ github.sha }} .
      - name: Build Frontend image
        run: docker build -f docker/Dockerfile.frontend -t hrms-frontend:${{ github.sha }} .
      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: hrms-api:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: 1

  # ── Deploy to Staging ──────────────────────────────────────────────
  deploy-staging:
    needs: docker-build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
      - name: Push images to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push $ECR_REGISTRY/hrms-api:${{ github.sha }}
      - name: Deploy to staging EKS
        run: |
          kubectl set image deployment/hrms-api hrms-api=$ECR_REGISTRY/hrms-api:${{ github.sha }} \
            -n staging

  # ── Deploy to Production (Manual Approval) ─────────────────────────
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production  # requires manual approval in GitHub
    steps:
      - name: Rolling update to production
        run: |
          kubectl set image deployment/hrms-api hrms-api=$ECR_REGISTRY/hrms-api:${{ github.sha }} \
            -n production
          kubectl rollout status deployment/hrms-api -n production --timeout=300s
```

## pytest Example (Unit + Integration)
```python
# tests/unit/test_cv_scorer.py
import pytest
from ai.cv_scorer import score_cv_against_jd, extract_features_from_text

class TestCVScorer:
    def test_perfect_match_score(self):
        """CV that matches all JD requirements should score 80+."""
        jd_text = "We need a Senior Python developer with 5+ years experience in FastAPI, PostgreSQL, Docker. Bachelor's degree required."
        cv_text = "Senior Software Engineer with 7 years Python experience. Expertise: FastAPI, PostgreSQL, Docker, Redis. BSc Computer Science."

        result = score_cv_against_jd(
            jd_text=jd_text,
            cv_text=cv_text,
            required_skills=["python", "fastapi", "postgresql", "docker"],
            min_experience_years=5,
        )

        assert result["overall_score"] >= 80
        assert "python" in result["matched_skills"]
        assert "fastapi" in result["matched_skills"]
        assert result["candidate_experience_years"] >= 5

    def test_missing_skills_reduces_score(self):
        jd_text = "Python developer needed with AWS and Kubernetes experience."
        cv_text = "Python developer. No cloud experience."

        result = score_cv_against_jd(
            jd_text=jd_text,
            cv_text=cv_text,
            required_skills=["python", "aws", "kubernetes"],
            min_experience_years=0,
        )

        assert result["overall_score"] < 70
        assert "aws" in result["missing_skills"]
        assert "kubernetes" in result["missing_skills"]

    def test_bias_detection_gender(self):
        cv_text = "Mr. John Smith. He/Him pronouns."
        result = extract_features_from_text(cv_text)
        assert result  # detection doesn't affect score

    def test_explanation_format(self):
        result = score_cv_against_jd(
            jd_text="Python developer",
            cv_text="Python engineer with 3 years experience",
            required_skills=["python"],
            min_experience_years=2,
        )
        assert "Score" in result["explanation"]
        assert "/100" in result["explanation"]


# tests/integration/test_employee_api.py
import pytest
from httpx import AsyncClient
from main import app
from tests.factories import EmployeeFactory, TenantFactory

@pytest.mark.asyncio
class TestEmployeeAPI:
    async def test_list_employees_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/employees")
        assert response.status_code == 401

    async def test_list_employees_tenant_isolation(
        self, client: AsyncClient, auth_headers_tenant_a, auth_headers_tenant_b
    ):
        """Tenant A should never see Tenant B's employees."""
        # Create employees in tenant A
        await EmployeeFactory.create_batch(5, tenant_id="tenant_a")
        await EmployeeFactory.create_batch(3, tenant_id="tenant_b")

        response_a = await client.get("/api/v1/employees", headers=auth_headers_tenant_a)
        response_b = await client.get("/api/v1/employees", headers=auth_headers_tenant_b)

        assert response_a.status_code == 200
        assert response_b.status_code == 200

        employees_a = response_a.json()["data"]
        employees_b = response_b.json()["data"]

        # Verify no cross-tenant leakage
        ids_a = {e["id"] for e in employees_a}
        ids_b = {e["id"] for e in employees_b}
        assert ids_a.isdisjoint(ids_b), "Tenant isolation violated!"
        assert len(employees_a) == 5
        assert len(employees_b) == 3

    async def test_pagination(self, client: AsyncClient, auth_headers):
        await EmployeeFactory.create_batch(30)
        response = await client.get(
            "/api/v1/employees?page=1&per_page=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["meta"]["total"] >= 30
        assert data["meta"]["pages"] >= 3
```
