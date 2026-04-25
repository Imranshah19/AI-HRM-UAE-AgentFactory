# SECTION 1 — SYSTEM ARCHITECTURE

## 1.1 Architecture Decision: Modular Monolith → Selective Microservices

### Why NOT pure microservices at launch
For a 500–5,000 employee HRMS, full microservices adds operational overhead
(service mesh, distributed tracing, inter-service latency) without proportional
benefit at this scale. Instead we use a **Modular Monolith** with clear domain
boundaries, deploying CPU/IO-heavy workloads (AI inference, payroll processing,
report generation) as **isolated async services** via Celery. This allows
independent scaling of expensive operations without the full microservices tax.

**Migration path**: Each module's internal boundary is clean enough to extract
into a true microservice post-PMF if a single domain becomes the bottleneck.

---

## 1.2 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLIENT LAYER                                                        │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────────┐  │
│  │ Next.js 14+   │  │ PWA (Phase 1) │  │ React Native (Phase 2) │  │
│  │ Web Dashboard │  │ Mobile Web    │  │ iOS + Android          │  │
│  └───────┬───────┘  └───────┬───────┘  └───────────┬────────────┘  │
└──────────┼──────────────────┼──────────────────────┼───────────────┘
           │ HTTPS / WSS      │ HTTPS                │ HTTPS / FCM
┌──────────▼──────────────────▼──────────────────────▼───────────────┐
│  API GATEWAY LAYER (Nginx + AWS ALB)                                │
│  • TLS termination (TLS 1.3)                                        │
│  • Rate limiting (per-IP, per-user, per-role)                       │
│  • Request routing: /api/v1/* → FastAPI, /ws/* → WebSocket          │
│  • DDoS protection via Cloudflare                                   │
│  • CORS enforcement, security headers injection                     │
│  • JWT token validation at gateway (lightweight pre-check)          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP/1.1 + HTTP/2
┌──────────────────────────────▼──────────────────────────────────────┐
│  APPLICATION LAYER (FastAPI — Modular Monolith)                     │
│                                                                      │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │  Employee   │ │Attendance│ │  Payroll  │ │   Recruitment    │   │
│  │  Module     │ │  Module  │ │  Module   │ │   Module (ATS)   │   │
│  └─────────────┘ └──────────┘ └───────────┘ └──────────────────┘   │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │   Leave     │ │Performanc│ │ Training  │ │   Self-Service   │   │
│  │  Module     │ │  Module  │ │  Module   │ │   Portal         │   │
│  └─────────────┘ └──────────┘ └───────────┘ └──────────────────┘   │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │   Asset     │ │Offboardi-│ │Compliance │ │  Notifications   │   │
│  │  Module     │ │ng Module │ │  Module   │ │  Module          │   │
│  └─────────────┘ └──────────┘ └───────────┘ └──────────────────┘   │
│  ┌─────────────┐ ┌──────────┐                                       │
│  │   Reports   │ │  Auth /  │ Cross-cutting: RBAC, Tenant,          │
│  │  & BI       │ │  RBAC    │ Audit, i18n, Feature Flags            │
│  └─────────────┘ └──────────┘                                       │
│                                                                      │
│  WebSocket Manager (real-time attendance, notifications)            │
└──────────────┬───────────────────────┬──────────────────────────────┘
               │ SQLAlchemy ORM        │ Celery task dispatch
┌──────────────▼───────────┐  ┌────────▼──────────────────────────────┐
│  DATA LAYER              │  │  ASYNC WORKER LAYER (Celery + Redis)   │
│                          │  │                                        │
│  PostgreSQL 15+          │  │  Payroll Engine Worker                 │
│  (primary OLTP)          │  │  Report Generation Worker              │
│  Redis Cluster           │  │  Email / SMS / WhatsApp Worker         │
│  (cache, sessions,       │  │  AI Inference Worker                   │
│   Celery broker)         │  │  Document Processing Worker            │
│  Elasticsearch 8+        │  │  Biometric Sync Worker                 │
│  (search, analytics)     │  │  ETL / Import Worker                   │
│  AWS S3 / MinIO          │  │  Notification Scheduler                │
│  (documents, payslips,   │  └────────────────────────────────────────┘
│   profile photos)        │
└──────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  AI SERVICES LAYER (Python — can be co-located or separate pods)    │
│                                                                      │
│  ┌────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │ CV Shortlist   │  │ Attrition Risk    │  │ Performance       │   │
│  │ Engine         │  │ Prediction        │  │ Prediction        │   │
│  │ (sentence-     │  │ (XGBoost +        │  │ (Random Forest)   │   │
│  │  transformers) │  │  SHAP)            │  │                   │   │
│  └────────────────┘  └───────────────────┘  └───────────────────┘   │
│  ┌────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │ HR Chatbot RAG │  │ NLQ Analytics     │  │ Fairness &        │   │
│  │ (LangChain +   │  │ (GPT / Claude API │  │ Explainability    │   │
│  │  pgvector)     │  │  + Recharts)      │  │ (SHAP + Audit)    │   │
│  └────────────────┘  └───────────────────┘  └───────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  INTEGRATION LAYER                                                   │
│  ZKTeco Biometric │ SendGrid/SES │ Twilio SMS │ Meta WhatsApp API   │
│  Google Calendar  │ LinkedIn API │ Indeed API │ Microsoft Graph     │
│  SAML 2.0 / SSO   │ IBFT/BACS/ACH bank export │ Moodle LMS API     │
└──────────────────────────────────────────────────────────────────────┘
```

## 1.3 Communication Protocols Per Layer

| Layer Boundary | Protocol | Notes |
|---|---|---|
| Browser ↔ API Gateway | HTTPS (TLS 1.3) | All traffic encrypted |
| Browser ↔ WebSocket | WSS (Secure WS) | Attendance live feed, notifications |
| Mobile PWA ↔ API | HTTPS + Service Worker | Offline caching via SW |
| API Gateway ↔ FastAPI | HTTP/2 (internal) | Keep-alive, multiplexing |
| FastAPI ↔ PostgreSQL | TCP (asyncpg driver) | Connection pool via PgBouncer |
| FastAPI ↔ Redis | TCP (aioredis) | Async, connection pooled |
| FastAPI ↔ Elasticsearch | HTTP REST (elasticsearch-py async) | |
| FastAPI ↔ Celery | Redis broker (AMQP protocol) | Task serialization: JSON |
| FastAPI ↔ S3/MinIO | HTTPS (boto3 async) | Pre-signed URLs for downloads |
| Celery Workers ↔ AI Services | Internal HTTP or direct function call | Same pod or sidecar |
| All Services ↔ Vault | HTTPS (hvac client) | Secrets fetched at startup |

## 1.4 Multi-Tenant Decision: Shared Schema with tenant_id

See Section 11 for full justification and implementation.
**Decision: Shared Schema (single DB, tenant_id on every table)**

Rationale for this scale (500–5000 employees across subsidiaries):
- Schema-per-tenant: too many schemas to manage (migrations become nightmares at 50+ tenants)
- DB-per-tenant: prohibitively expensive for 50+ small subsidiaries
- Shared schema: single migration, connection pooling shared, tenant isolation enforced
  at application layer via FastAPI dependency injection — lowest ops overhead
  at this scale while still fully secure if implemented correctly

## 1.5 Deployment Topology

```
Internet → Cloudflare (DDoS, CDN) → AWS ALB
  → Nginx Ingress (K8s)
    → FastAPI Pods (3 replicas min, HPA to 20)
    → Celery Worker Pods (per queue, spot instances)
    → Next.js SSR Pods (2 replicas min)
  → RDS PostgreSQL (Multi-AZ)
  → ElastiCache Redis (cluster mode)
  → OpenSearch (3 node cluster)
  → S3 (cross-region replication enabled)
```
