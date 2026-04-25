# Section 1: System Architecture

## 1.1 Architecture Decision: Modular Monolith → Microservices Migration Path

### Why NOT pure microservices from day one

For a 500–5000 employee HRMS with a team building from scratch, a **modular monolith** deployed as independently scalable services is the correct starting point:

- Pure microservices add 40–60% infrastructure overhead before you understand domain boundaries
- HRMS data is deeply relational (payroll depends on attendance, leave, salary structure simultaneously)
- Cross-service transactions (e.g., run payroll → deduct leave encashment → update salary) are complex with distributed sagas
- **Decision:** Single deployable FastAPI app with strict internal module boundaries, extracted to microservices in Phase 2 when bottlenecks are identified

The architecture is designed so each "service" is a FastAPI Router with its own database models, Celery tasks, and Redis namespaces — making future extraction straightforward.

---

## 1.2 Layered Architecture Diagram

```
════════════════════════════════════════════════════════════════════════
LAYER 1: CLIENT LAYER
════════════════════════════════════════════════════════════════════════

┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐
│   Web Application   │  │   Mobile PWA /       │  │  Admin Console   │
│   Next.js 14        │  │   React Native       │  │  Next.js 14      │
│   App Router + SSR  │  │   Expo SDK 50+       │  │  Super Admin     │
│   TailwindCSS       │  │   Offline-first      │  │  Only           │
│   shadcn/ui         │  │   Biometric login    │  │                  │
│   React Query       │  │   FCM / APNs         │  │                  │
│   Zustand           │  │                      │  │                  │
└─────────────────────┘  └─────────────────────┘  └──────────────────┘
          │                        │                        │
          └────────────────────────┴────────────────────────┘
                                   │ HTTPS (TLS 1.3)
                                   │ WebSocket (WSS)
                                   ↓

════════════════════════════════════════════════════════════════════════
LAYER 2: EDGE & API GATEWAY LAYER
════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────────┐
│                  Cloudflare CDN / AWS CloudFront                     │
│   Static Assets · DDoS Protection · WAF · Geo-routing               │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                               │
│   SSL Termination · Load Balancing · Upstream Health Check           │
│   /api/* → FastAPI    /ws/* → WebSocket    /* → Next.js             │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────┐
│                      Kong API Gateway                                │
│   Rate Limiting (per-role, per-endpoint)                            │
│   JWT Validation · CORS Policy · Request Logging                    │
│   IP Allowlisting (admin routes) · API Key auth (integrations)      │
│   Circuit Breaker · Request/Response Transformation                 │
└──────────────────────────────────────────────────────────────────────┘
                                   │

════════════════════════════════════════════════════════════════════════
LAYER 3: APPLICATION SERVICES LAYER (FastAPI Modular Monolith)
════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 Cross-Cutting Concerns                       │   │
│  │  Auth Middleware · Audit Middleware · i18n · Error Handler   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │Employee  │ │Attendance│ │ Payroll  │ │Recruit-  │ │ Leave   │  │
│  │Module    │ │Module    │ │Module    │ │ment (ATS)│ │Module   │  │
│  │/employee │ │/attend   │ │/payroll  │ │/recruit  │ │/leave   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘  │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │Performan-│ │Training  │ │Self-     │ │ Assets   │ │Offboard │  │
│  │ce Module │ │Module    │ │Service   │ │Module    │ │Module   │  │
│  │/perf     │ │/training │ │/self-svc │ │/assets   │ │/offboard│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘  │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                           │
│  │Compliance│ │Notificat-│ │Analytics │                           │
│  │Module    │ │ions      │ │Module    │                           │
│  │/comply   │ │/notify   │ │/analytics│                           │
│  └──────────┘ └──────────┘ └──────────┘                           │
└─────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════
LAYER 4: ASYNC WORKER LAYER
════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                    Celery Worker Pool                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │Payroll Queue │  │ Email Queue  │  │  Report Generation Queue │  │
│  │(low concurr) │  │(high concurr)│  │  (CPU-bound workers)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ AI Inference │  │ Data Sync    │  │  Celery Beat (Scheduler) │  │
│  │ Queue        │  │ Queue        │  │  Cron-like periodic tasks│  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════
LAYER 5: AI SERVICES LAYER
════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                        AI Service Pods                              │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐ │
│  │  CV Shortlisting Service │  │  Attrition Prediction Service    │ │
│  │  BERT Embeddings         │  │  XGBoost Model (scikit-learn)    │ │
│  │  Cosine Similarity       │  │  SHAP Explainability             │ │
│  │  SHAP Explanation        │  │  Feature Engineering Pipeline    │ │
│  └──────────────────────────┘  └──────────────────────────────────┘ │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐ │
│  │  HR Chatbot Service      │  │  Analytics NLQ Service           │ │
│  │  LangChain + RAG         │  │  NL → SQL Translation            │ │
│  │  Pinecone/pgvector       │  │  Anomaly Detection               │ │
│  │  GPT-4o / Claude API     │  │  Chart Generation                │ │
│  └──────────────────────────┘  └──────────────────────────────────┘ │
│  ┌──────────────────────────┐                                       │
│  │  Performance Prediction  │                                       │
│  │  Random Forest (sklearn) │                                       │
│  │  Quarterly retraining    │                                       │
│  └──────────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════
LAYER 6: DATA LAYER
════════════════════════════════════════════════════════════════════════

┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────────┐
│ PostgreSQL   │ │    Redis     │ │Elasticsearch│ │  AWS S3 /      │
│ 15+ Primary  │ │  6.x         │ │  8.x        │ │  MinIO         │
│              │ │              │ │             │ │                │
│ ·employees   │ │ ·Sessions    │ │ ·CV search  │ │ ·Payslip PDFs  │
│ ·payroll     │ │ ·Rate limits │ │ ·Employee   │ │ ·Documents     │
│ ·attendance  │ │ ·Celery brkr │ │  directory  │ │ ·Profile pics  │
│ ·leave       │ │ ·Real-time   │ │ ·Audit logs │ │ ·Certificates  │
│ ·performance │ │  attendance  │ │ ·Analytics  │ │ ·Asset photos  │
│ ·audit_logs  │ │ ·Cache layer │ │  aggregation│ │                │
│ Read Replica │ │ Redis Cluster│ │ 3-node clus │ │ Versioned +    │
│ (reporting)  │ │              │ │             │ │ Encrypted      │
└──────────────┘ └──────────────┘ └─────────────┘ └────────────────┘
      │
      │ pgvector extension
      ↓
┌──────────────┐
│ Vector Store │
│ (pgvector or │
│  Pinecone)   │
│ ·HR policy   │
│  embeddings  │
│ ·CV embeddings│
└──────────────┘

════════════════════════════════════════════════════════════════════════
LAYER 7: INTEGRATION LAYER
════════════════════════════════════════════════════════════════════════

┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────────┐
│  Biometric   │ │ Comm Channel │ │  Calendar   │ │  Job Boards    │
│  ZKTeco SDK  │ │ SendGrid/SES │ │  Google Cal │ │  LinkedIn API  │
│  ZKOSS REST  │ │ Twilio SMS   │ │  MS Graph   │ │  Indeed API    │
│  WebPush SDK │ │ Meta WA API  │ │  Outlook    │ │                │
└──────────────┘ └──────────────┘ └─────────────┘ └────────────────┘
┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────────┐
│  Identity    │ │ Bank Export  │ │  LMS        │ │  Monitoring    │
│  OAuth2/SAML │ │ IBFT format  │ │  Moodle API │ │  Prometheus    │
│  Google SSO  │ │ BACS/ACH     │ │  SCORM xAPI │ │  Grafana       │
│  Azure AD    │ │              │ │             │ │  Sentry        │
└──────────────┘ └──────────────┘ └─────────────┘ └────────────────┘
```

---

## 1.3 Communication Protocols

| Communication Type | Protocol | Details |
|-------------------|----------|---------|
| Client ↔ API | HTTPS REST | TLS 1.3, JSON payloads, versioned /api/v1/ |
| Real-time attendance | WebSocket (WSS) | FastAPI WebSocket, Redis pub/sub backend |
| Real-time notifications | Server-Sent Events (SSE) | Lightweight, one-directional, auto-reconnect |
| Celery tasks | Redis/AMQP | Reliable message passing, result backend |
| Service-to-service | Internal HTTP | Within same pod/container, no auth overhead |
| Biometric device | ZKTeco REST API | Polling every 30s + webhook on event |
| External APIs | HTTPS REST | SendGrid, Twilio, LinkedIn, Google APIs |
| AI model inference | gRPC (Python) | Low-latency internal calls to AI pods |

---

## 1.4 Request Flow — Standard API Call

```
Browser/Mobile
     │
     │ HTTPS POST /api/v1/leave/apply
     ↓
Cloudflare (WAF, DDoS, CDN)
     │
     ↓
Nginx (SSL termination, upstream routing)
     │
     ↓
Kong API Gateway
     │  ├─ Rate limit check (Redis counter)
     │  ├─ JWT validation (RS256, check expiry)
     │  ├─ CORS validation
     │  └─ Request logging (ELK)
     ↓
FastAPI Leave Router
     │  ├─ Dependency: verify_token() → extract user_id, role
     │  ├─ Permission check: has_permission(role, "leave:create")
     │  ├─ Pydantic request validation
     │  ├─ Business logic: check leave balance, detect conflicts
     │  ├─ DB write: INSERT into leave_requests
     │  ├─ Audit log: INSERT into audit_logs
     │  └─ Celery task: send approval notification email (async)
     ↓
JSON Response → 201 Created
```

---

## 1.5 Real-time Attendance Flow

```
ZKTeco Device (biometric punch)
     │
     │ HTTP POST /webhook/attendance (ZKTeco push)
     ↓
FastAPI Attendance Webhook Handler
     │  ├─ Validate device signature
     │  ├─ INSERT attendance_records
     │  └─ Redis PUBLISH to channel "attendance:live"
     ↓
Redis Pub/Sub channel
     │
     ↓
FastAPI WebSocket Handler (broadcast)
     │  └─ For each connected WebSocket client with permission:
     │       ws.send_json(attendance_update)
     ↓
HR Dashboard Browser (real-time update via WebSocket)
```

---

## 1.6 Multi-Tenancy Design

```
Tenant Isolation Strategy: Schema-per-tenant (PostgreSQL schemas)

├── public (shared: auth, tenant registry)
├── tenant_acme (ACME Corp data)
│   ├── employees
│   ├── payroll_records
│   └── ... (all tables)
├── tenant_globex (Globex Corp data)
│   ├── employees
│   ├── payroll_records
│   └── ...
```

**Middleware approach:**
```python
# tenant_middleware.py
async def tenant_middleware(request: Request, call_next):
    tenant_id = extract_tenant_from_jwt(request.headers["Authorization"])
    request.state.tenant_schema = f"tenant_{tenant_id}"
    # Set PostgreSQL search_path per request
    async with db.connect() as conn:
        await conn.execute(f"SET search_path TO tenant_{tenant_id}, public")
    return await call_next(request)
```

---

## 1.7 Scalability Design

| Component | Scaling Strategy | Trigger |
|-----------|-----------------|---------|
| FastAPI app | Horizontal pod scaling (HPA) | CPU > 70% or req/s > 500 |
| Celery workers | Queue depth-based autoscaling | Queue depth > 100 tasks |
| PostgreSQL | Read replicas for reporting queries | Read load > 60% |
| Redis | Redis Cluster (3 primary + 3 replica) | Memory > 70% |
| Elasticsearch | 3-node cluster with shard routing | Index size / query latency |
| AI services | Separate pod pool, GPU-enabled nodes | Inference queue depth |

**Stateless API guarantee:**
- No in-memory session state — all session data in Redis
- JWT tokens are self-contained — no DB lookup per request
- File uploads go directly to S3 (presigned URLs) — API doesn't handle file bytes
- Sticky sessions explicitly disabled at load balancer

---

## 1.8 Zero-Downtime Deployment Strategy

```
Rolling deployment (Kubernetes):
  1. New pods start alongside old pods
  2. Health check: /health endpoint must return 200
  3. Traffic gradually shifts (25% → 50% → 75% → 100%)
  4. Old pods terminate after draining connections (graceful shutdown 30s)

Database migrations (Alembic):
  - Migrations must be backward-compatible (add columns nullable first)
  - Never rename/drop columns in same release as code change
  - Blue-green schema migration for breaking changes

Feature flags (LaunchDarkly / custom):
  - New AI features gated behind feature flags
  - Gradual rollout by tenant or user role
```
