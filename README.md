# FileBRSR

ESG / BRSR compliance SaaS for Indian listed companies. Upload an annual report → AI extracts the
337 BRSR datapoints SEBI requires, scores compliance, generates the filing PDF/XBRL, and
benchmarks against NIFTY 50 peers.

Live: <https://www.filebrsr.com>

---

## Table of contents

1. [What it does](#what-it-does)
2. [Tech stack](#tech-stack)
3. [Repository layout](#repository-layout)
4. [Local development](#local-development)
5. [Architecture](#architecture)
6. [Request flow (end-to-end)](#request-flow-end-to-end)
7. [Backend endpoints](#backend-endpoints)
8. [Database](#database)
9. [Environment variables](#environment-variables)
10. [Branching, CI/CD and deploy](#branching-cicd-and-deploy)
11. [Rolling back](#rolling-back)
12. [Operations runbook](#operations-runbook)
13. [Known gaps / roadmap](#known-gaps--roadmap)
14. [Glossary](#glossary)

---

## What it does

| User flow | Outcome |
|---|---|
| Upload a PDF annual report | AI pulls all 337 BRSR datapoints (Sections A/B/C, principles P1–P9) |
| Review / edit extracted data | Side-by-side editor with confidence scores and source page references |
| Score compliance | Coverage %, gap analysis, mandatory vs. core vs. leadership splits |
| Benchmark | Compare against NIFTY 50 sector benchmarks |
| Generate filings | SEBI-format PDF + XBRL + Excel exports |
| Track org | Multi-tenant teams, role-based access, plan tiers (billing via Razorpay) |

---

## Tech stack

### Frontend
- **Next.js 16.2.6** (App Router, React 19, Turbopack)
- **TailwindCSS 4** + **Lucide** icons
- **Supabase JS** (`@supabase/ssr` for cookie-based auth)
- **Recharts** for dashboards
- **Sentry** (client + edge + server) + **PostHog** product analytics
- **Playwright** for E2E smoke tests
- Container: standalone Next.js build, port 3000

### Backend
- **FastAPI 0.115** + **uvicorn**, Python 3.12
- **pdfplumber** for layout-aware PDF extraction
- AI providers: **Anthropic Claude**, **Google Gemini**, **Groq**, **AWS Bedrock**
- **Supabase Python** client for DB / auth-verify
- **Sentry SDK**, in-process IP rate limiter for guest endpoints
- Container: same image for `backend` (uvicorn) and `worker` (`python -m app.worker`), port 8000

### Data & infra
- **Supabase** — Postgres, Auth (JWT via JWKS), Storage, RLS
- **AWS**
  - EC2 (Mumbai, `ap-south-1`) — single host today
  - ECR — private image registry
  - IAM — `filebrsr-gha-ecr` (CI push), `filebrsr-ec2-bedrock` (EC2 pull + Bedrock)
- **nginx:alpine** in front of frontend + backend (TLS, gzip, rate limit)
- **certbot** — Let's Encrypt renewal sidecar
- **GitHub Actions** — lint, test, build, push to ECR, SSH deploy

### Third-party services
- **Razorpay** — payments
- **Resend** — transactional email
- **Sentry** — error tracking + uptime monitoring
- **PostHog** — product analytics

---

## Repository layout

```
filebrsr/
├── backend/                    FastAPI service
│   ├── app/
│   │   ├── main.py             ASGI app, top-level routes, middleware, CORS
│   │   ├── config.py           Pydantic Settings (env-driven)
│   │   ├── worker.py           Background job loop (poll Supabase queue table)
│   │   ├── extraction*.py      Regex / enhanced / AI / agent extraction strategies
│   │   ├── ai_extraction.py    LLM call wrappers (Claude/Gemini/Groq)
│   │   ├── brsr_*.py           BRSR framework definition, datapoints catalog
│   │   ├── router_*.py         Mounted FastAPI routers (one per domain)
│   │   ├── billing.py          Razorpay integration + plan-tier checks
│   │   ├── scoring.py          Compliance scoring engine
│   │   ├── pdf_generator.py    Compliance report PDF
│   │   ├── sebi_pdf_*.py       SEBI-format filing PDF
│   │   ├── xbrl_*.py           XBRL filing export
│   │   ├── excel_import.py     XLSX ingest / export
│   │   ├── nifty50_benchmarks.py  Sector benchmark data
│   │   ├── cross_framework_mapping.py  BRSR ↔ ESRS / GRI / TCFD
│   │   └── email_service.py    Resend wrapper
│   ├── tests/                  pytest suite (22 tests)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── ruff.toml               Lint/format config (standalone, no [tool.ruff])
│   └── pytest.ini
│
├── frontend/                   Next.js 16 app
│   ├── src/
│   │   ├── middleware.ts       Supabase auth refresh on every request
│   │   ├── app/                App Router (pages + route handlers)
│   │   │   ├── api/            Server-only API proxy routes
│   │   │   ├── login/, auth/, dashboard/, demo/, pricing/, …
│   │   │   └── platform/       Multi-tenant admin
│   │   ├── components/         Shared UI
│   │   └── lib/                supabase client, posthog init, utils
│   ├── e2e/                    Playwright smoke
│   ├── sentry.{client,server,edge}.config.ts
│   ├── next.config.ts          standalone output, sentry plugin
│   ├── Dockerfile              multi-stage, build args for NEXT_PUBLIC_*
│   └── playwright.config.ts
│
├── nginx/
│   └── nginx.conf              TLS, rate limits, /backend rewrite
│
├── supabase/                   SQL schema + migrations (numbered v2..v9)
│   ├── schema.sql
│   ├── migration_v*.sql
│   └── admin_grants.sql.local  (gitignored) local admin role grants
│
├── scripts/                    Ops scripts
│   ├── aws-setup.sh            One-time: create ECR repos + IAM user
│   ├── deploy.sh               Runs on EC2 via SSH from CI
│   └── rollback.sh             Manual rollback to previous (or chosen) tag
│
├── docs/                       Pitch decks, gap analysis whitepaper, architecture diagrams
├── sebi_doc/                   SEBI BRSR reference text
├── refrence_report/            Sample reports used as fixtures
│
├── docker-compose.prod.yml     Production compose (image: pull-only from ECR)
├── deploy-gcp.sh               Legacy GCP deploy (unused)
├── .github/workflows/ci.yml    GitHub Actions pipeline
└── README.md                   ← you are here
```

---

## Local development

### Prerequisites
- macOS or Linux
- Docker (only if running prod-style)
- Python 3.12 + venv
- Node 20+ (or 22)
- A Supabase project (free tier works) — you'll need URL + anon key + service-role key

### One-time setup

```bash
# clone
git clone github-personal:ydvikasiitkgp-arch/filebrsr.git
cd filebrsr

# backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp ../supabase/admin_grants.sql.local.example admin_grants.sql.local  # if you need admin perms locally
# create backend/.env (see "Environment variables" below)

# frontend
cd ../frontend
npm install
# create frontend/.env.local (see "Environment variables" below)
```

### Run locally

Two terminals, no Docker:

```bash
# terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# terminal 2 — frontend
cd frontend
npm run dev
# → http://localhost:3000
```

Worker (optional, only if you're testing async jobs):

```bash
cd backend && source .venv/bin/activate
python -m app.worker
```

### Tests

```bash
# backend
cd backend && pytest                                 # 22 tests
ruff check app/                                      # lint (currently many findings — non-blocking)
ruff format --check app/                             # format check

# frontend
cd frontend
npm run lint                                         # ESLint (Next 16 ruleset)
npm run test:e2e                                     # Playwright smoke
```

### Database

Supabase is **managed** — you don't run Postgres locally. Apply migrations through the Supabase
SQL editor in order:

```
schema.sql           → migration_v2 → v3_plan_tiers → v3_platform → v3_rls_admin
                     → v4_advanced  → v5_settings   → v6_fix_entries
                     → v7_teams_analytics → v8_moat → v9_gtm
```

---

## Architecture

```
                              ┌───────────────────────────────────────────────┐
                              │              GitHub Actions (CI/CD)           │
                              │  push to main → build → push to ECR → SSH     │
                              └──────────────────┬────────────────────────────┘
                                                 │
       ┌─────────────────────────────────────────┴─────────────────────────────┐
       │                                                                       │
       ▼                                                                       ▼
┌─────────────────┐                                              ┌──────────────────────┐
│  Amazon ECR     │                                              │ Single EC2 (ap-south-1)│
│  frontend:<sha> │ ◄────────── docker pull ─────────────────── │ docker compose:       │
│  backend:<sha>  │                                              │   nginx (80/443)      │
└─────────────────┘                                              │   frontend (3000)     │
                                                                  │   backend  (8000)     │
       ┌─────────────────┐                                        │   worker              │
       │   End User      │ ──── https://www.filebrsr.com ───────► │   certbot             │
       │   (browser)     │                                        └─────────┬────────────┘
       └─────────────────┘                                                  │
                                                                            ▼
                                                            ┌─────────────────────────────┐
                                                            │  External SaaS              │
                                                            │   • Supabase (DB+auth)      │
                                                            │   • Gemini / Groq / Claude  │
                                                            │   • AWS Bedrock             │
                                                            │   • Resend (email)          │
                                                            │   • Razorpay (payments)     │
                                                            │   • Sentry, PostHog         │
                                                            └─────────────────────────────┘
```

| Layer | Component | Where |
|---|---|---|
| DNS | `filebrsr.com` + `www` → `13.207.133.255` (EC2 EIP) | external registrar |
| Edge | nginx + certbot | [nginx/nginx.conf](nginx/nginx.conf) |
| Web | Next.js standalone | [frontend/](frontend/) |
| API | FastAPI + uvicorn | [backend/app/main.py](backend/app/main.py) |
| Workers | Same backend image, `python -m app.worker` | [backend/app/worker.py](backend/app/worker.py) |
| Data | Supabase managed Postgres | [supabase/](supabase/) |
| Object storage | Supabase storage buckets | external |
| Secrets | `.env` on EC2 (⚠ plaintext, see gaps) | `/home/ec2-user/filebrsr/.env` |
| CI/CD | GitHub Actions → ECR → SSH | [.github/workflows/ci.yml](.github/workflows/ci.yml) |

---

## Request flow (end-to-end)

```
1. Browser → DNS lookup → 13.207.133.255
2. TCP 443 → EC2 → nginx container (TLS termination, rate limit, gzip)
3. nginx routes:
     location /          → frontend:3000  (everything page-related, incl. /api/*)
     location /backend/  → backend:8000   (rewritten — direct backend bypass)
4. Next.js renders the page (SSR/RSC). Server components fetch backend via
   internal DNS:  http://backend:8000  (set by BACKEND_URL env var)
5. Browser JS calls /api/* → Next.js route handler → forwards to backend
6. Backend:
     • verify JWT (Supabase JWKS)
     • run business logic
     • read/write Supabase
     • call LLM provider if extraction
     • enqueue async work in a Supabase table
7. Worker container polls the queue table → does long-running work →
   writes results back to Supabase
8. Frontend receives results via polling or Supabase realtime subscription
```

### Example: PDF extraction
```
POST /api/extract  (multipart, PDF in body, JWT in cookie)
  → nginx /  → frontend:3000  (route handler)
  → backend:8000 /api/extract
      → pdfplumber pulls text
      → ai_extraction.extract_with_ai()  (Gemini/Claude/Groq)
      → INSERT extraction job + initial datapoints into Supabase
      → return job_id
  → worker picks up job → runs agent_extraction → updates rows
  → frontend polls for completion
```

---

## Backend endpoints

Top-level routes ([backend/app/main.py](backend/app/main.py)):

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET  | `/health` | Liveness (used by docker healthcheck) | none |
| POST | `/api/extract` | Authenticated extraction | JWT |
| POST | `/api/guest-extract` | Demo extraction (IP-rate-limited 3/day) | none |
| GET  | `/api/framework` | BRSR framework definition | none |
| GET  | `/api/datapoints` | Full datapoint catalog | none |
| GET  | `/api/datapoints/esrs-mapping` | BRSR ↔ ESRS cross-mapping | none |
| POST | `/api/gap-analysis` | Compute coverage gaps | JWT |
| GET  | `/api/benchmarks` | NIFTY 50 benchmark roll-up | none |
| GET  | `/api/benchmarks/{sector}` | Sector benchmarks | none |

Mounted routers (each module is `router_*.py` in `backend/app/`):

| Router | Module | Domain |
|---|---|---|
| billing | [billing.py](backend/app/billing.py) | Razorpay, plan tiers |
| v2 | [router_v2.py](backend/app/router_v2.py) | New report generation API |
| platform | [router_platform.py](backend/app/router_platform.py) | Multi-tenant admin |
| advanced | [router_advanced.py](backend/app/router_advanced.py) | Advanced analytics |
| org | [router_org.py](backend/app/router_org.py) | Org/team management |
| moat | [router_moat.py](backend/app/router_moat.py) | Moat scoring |
| market | [router_market.py](backend/app/router_market.py) | Market & peer data |
| excel_import | [excel_import.py](backend/app/excel_import.py) | XLSX ingest |
| cron | [router_cron.py](backend/app/router_cron.py) | Scheduled tasks |
| xbrl | [xbrl_export.py](backend/app/xbrl_export.py) | XBRL export |
| xbrl_filing | [xbrl_filing.py](backend/app/xbrl_filing.py) | XBRL submission |
| sebi_pdf | [sebi_pdf_filing.py](backend/app/sebi_pdf_filing.py) | SEBI PDF |
| trends | [router_trends.py](backend/app/router_trends.py) | Trend analytics |

Interactive API docs: <http://localhost:8000/docs> when running locally.

---

## Database

- All schema in [supabase/](supabase/). `schema.sql` is the baseline; numbered `migration_v*.sql`
  files are applied in order.
- Row Level Security is on for tenant tables — see [supabase/migration_v3_rls_admin.sql](supabase/migration_v3_rls_admin.sql).
- Backend connects with the **service role key** (bypasses RLS); frontend uses the **anon key**
  with cookie-bound JWT (RLS enforced).

---

## Environment variables

### Backend (`backend/.env`)

| Var | Required | Notes |
|---|---|---|
| `SUPABASE_URL` | ✅ | e.g. `https://xxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | ✅ | service-role JWT (server-only — bypasses RLS) |
| `SUPABASE_JWT_SECRET` | ✅ | for verifying user JWTs |
| `GEMINI_API_KEY` | ✅ | primary extraction LLM |
| `GROQ_API_KEY` | optional | fallback LLM |
| `ANTHROPIC_API_KEY` | optional | premium extraction tier |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | for billing | |
| `RESEND_API_KEY` | for email | |
| `ALLOWED_ORIGINS` | ✅ | comma-separated CORS allow-list |
| `MAX_FILE_SIZE_MB` | default 50 | upload cap |
| `SENTRY_DSN` | optional | enables Sentry |
| `ENVIRONMENT` | default `development` | `production` in prod |

See [backend/app/config.py](backend/app/config.py).

### Frontend (`frontend/.env.local`)

| Var | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | public, baked into build |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | public, baked into build |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | server-only |
| `BACKEND_URL` | ✅ | `http://backend:8000` in prod, `http://localhost:8000` locally |
| `NEXT_PUBLIC_API_URL` | optional | leave empty to use same-origin |
| `NEXT_PUBLIC_POSTHOG_KEY` | optional | enables PostHog if set |
| `SENTRY_AUTH_TOKEN` | CI only | for source-map upload |

In production these are stored as **GitHub repo secrets** and injected at build / SSH time
(see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

---

## Branching, CI/CD and deploy

### Branch model

```
dev    ← daily work, all commits land here
 │
 │   git checkout main && git merge --no-ff dev -m "Merge branch 'dev'"
 ▼
main   ← every push triggers production deploy
```

- Push to `dev` → CI runs lint + tests, **does not deploy**
- Push to `main` → CI runs lint + tests, builds images, pushes to ECR, deploys to EC2

### Pipeline ([.github/workflows/ci.yml](.github/workflows/ci.yml))

```
┌──────────────────────────┐     ┌──────────────────────────┐
│ frontend-lint-build      │     │ backend-lint-test         │
│  • npm ci                │     │  • pip install            │
│  • npm run lint*         │     │  • ruff check*            │
│  • npm run build         │     │  • ruff format --check*   │
└────────────┬─────────────┘     │  • pytest (blocking)      │
             │                   └─────────────┬────────────┘
             └─────────────┬───────────────────┘
                           ▼
                  ┌─────────────────────────────────────────┐
                  │  deploy (main branch only)              │
                  │  1. Configure AWS creds (static keys)   │
                  │  2. ECR login                           │
                  │  3. Buildx build & push:                │
                  │       filebrsr-frontend:<sha> + :latest │
                  │       filebrsr-backend:<sha>  + :latest │
                  │     (with registry cache for speed)     │
                  │  4. scp compose + nginx + scripts → EC2 │
                  │  5. ssh ./scripts/deploy.sh             │
                  └─────────────────────────────────────────┘

* = continue-on-error (currently non-blocking — lint cleanup pending)
```

### What `deploy.sh` does on the box ([scripts/deploy.sh](scripts/deploy.sh))

1. `aws ecr get-login-password | docker login …`
2. Read previous `.current_tag` (for rollback target)
3. `docker compose pull frontend backend worker`
4. Write `TAG=` and `ECR_REGISTRY=` to `.env`
5. `docker compose up -d --force-recreate frontend backend worker`
6. `docker compose up -d nginx certbot` (only restarts if config changed)
7. Poll `docker inspect --format='{{.State.Health.Status}}'` for 60s
8. If unhealthy → roll back to previous tag and exit 1
9. If healthy → write new tag to `.current_tag`, `docker image prune -af --filter "until=168h"`

### Required GitHub secrets

| Secret | Used by |
|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | ECR push (TODO: migrate to OIDC) |
| `ECR_REGISTRY` | `755352605482.dkr.ecr.ap-south-1.amazonaws.com` |
| `EC2_HOST` | EC2 public DNS / IP |
| `EC2_SSH_KEY` | SSH private key for `ec2-user` |
| `NEXT_PUBLIC_SUPABASE_URL` | Next.js build arg |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Next.js build arg |
| `NEXT_PUBLIC_POSTHOG_KEY` | optional — empty disables PostHog |

---

## Rolling back

```bash
ssh ec2-user@<EC2_HOST>
cd ~/filebrsr
./scripts/rollback.sh                # roll back to .previous_tag
./scripts/rollback.sh <git-sha>      # roll back to a specific image tag
./scripts/rollback.sh                # with no .previous_tag → lists last 10 ECR tags
```

---

## Operations runbook

### Where things live
- App root on EC2: `/home/ec2-user/filebrsr/`
- Runtime secrets: `/home/ec2-user/filebrsr/.env`
- Let's Encrypt certs: `/etc/letsencrypt/live/filebrsr.com/`
- Container logs: `docker logs <container>`
- Active tag: `cat .current_tag`
- Rollback target: `cat .previous_tag`

### Common commands (on EC2)

```bash
# Status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Logs
docker logs --tail 100 -f filebrsr-backend-1
docker logs --tail 100 -f filebrsr-frontend-1
docker logs --tail 100 -f filebrsr-nginx-1
docker logs --tail 100 -f filebrsr-worker-1

# Disk
df -h /
docker system df

# Cache cleanup (we had a disk-full incident — do this if df > 80%)
docker system prune -f
docker builder prune -af
docker image prune -af --filter "until=168h"

# Healthcheck details
docker inspect filebrsr-backend-1 --format '{{json .State.Health}}' | jq

# Reload nginx after editing nginx.conf
docker compose -f docker-compose.prod.yml up -d nginx
```

### Smoke test (the user is behind Zscaler which blocks filebrsr.com — test from EC2 itself)

```bash
ssh ec2-user@<EC2_HOST> '
  for p in / /pricing /login /demo /contact; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Host: www.filebrsr.com" "https://localhost$p")
    echo "$p -> $code"
  done
  curl -s http://localhost:8000/health
'
```

### Cert renewal

`certbot` sidecar renews automatically. To force:

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Observability (metrics + dashboards)

The backend exposes Prometheus metrics at `GET /metrics` (RED metrics for every
HTTP request plus domain counters):

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `filebrsr_http_requests_total` | counter | `method,path,status` | requests by route template |
| `filebrsr_http_request_duration_seconds` | histogram | `method,path` | request latency |
| `filebrsr_prov_signatures_total` | counter | — | provenance signing ops |
| `filebrsr_prov_verifications_total` | counter | `result` | public verify PASS/FAIL |
| `filebrsr_ledger_appends_total` | counter | `result` | Merkle ledger appends |
| `filebrsr_extractions_total` | counter | `result` | extraction pipeline runs |

`path` is always the matched **route template** (e.g. `/api/verify/{calculation_id}`),
never a raw URL, to keep Prometheus label cardinality bounded. The `/metrics`
endpoint is internal (scraped from the backend container; not proxied publicly
via nginx).

### Run the local stack

With the backend running on `localhost:8000`:

```bash
docker compose -f observability/docker-compose.observability.yml up
# Grafana    → http://localhost:3001  (admin / admin)
# Prometheus → http://localhost:9090
```

If those host ports are taken, override them:

```bash
PROM_PORT=9091 GRAFANA_PORT=3005 \
  docker compose -f observability/docker-compose.observability.yml up
```

Grafana auto-provisions the Prometheus datasource and the **FileBRSR — Service
Overview** dashboard (request rate, error ratio, p50/p95/p99 latency,
verification outcomes, signing / ledger / extraction counters). Config lives in
`observability/`.

### In production

The prod stack ([docker-compose.prod.yml](docker-compose.prod.yml)) runs
`prometheus` + `grafana` alongside the app. Grafana is served privately at
**https://filebrsr.com/grafana/** behind its own admin login; the backend
`/metrics` surface is internal-only (nginx returns 404 for `/backend/metrics`;
Prometheus scrapes `backend:8000` over the compose network).

Grafana defaults to `admin` / `admin` on first login and prompts for a new
password. To set credentials up front instead, add to the EC2 `~/filebrsr/.env`:

```bash
# both optional — default to "admin":
# GRAFANA_ADMIN_USER=<user>
# GRAFANA_ADMIN_PASSWORD=<strong-password>
```

---

## Known gaps / roadmap

See full breakdown earlier in this session, summary here:

**P0 — incidents waiting to happen**
1. Single EC2 in a single AZ — full outage on instance/AZ failure
2. No CloudWatch alarms (disk, mem, CPU, container restart) — last disk-full incident was caught only by manual log spelunking
3. Secrets stored as plaintext `.env` on disk
4. Static AWS keys for CI — migrate to GitHub OIDC
5. No EBS snapshot lifecycle — RTO depends on you remembering how the box was set up

**P1 — operational hygiene**
6. CI lint is non-blocking — sweep up `react-hooks/set-state-in-effect` + 358 ruff findings
7. No staging environment (`dev.filebrsr.com` from `dev` branch)
8. No SLO/SLI defined
9. No log aggregation (CloudWatch / Datadog / Loki)
10. GitHub Actions on Node 20 — deprecated June 2026
11. Database migrations applied manually — no CI gate
12. Worker has no healthcheck / heartbeat — silent failure mode

**P2 — scale & cost**
13. Frontend + backend + worker on the same 4 vCPU box
14. No CDN — every static asset served from nginx on a single EC2
15. No WAF at edge
16. PII not actively redacted in Sentry payloads

**Recommended next 4 things, in order**
1. OIDC for GitHub Actions (kill static AWS keys)
2. CloudWatch alarms (5 alarms cover 80% of incident classes)
3. AWS Secrets Manager (get secrets off the disk)
4. ALB + second EC2 in a second AZ — OR migrate to ECS Fargate

---

## Glossary

| Term | Meaning |
|---|---|
| **BRSR** | Business Responsibility & Sustainability Report — SEBI-mandated ESG disclosure for top 1,000 listed Indian companies |
| **Section A/B/C** | BRSR document structure: A = general, B = management & process, C = principle-wise (P1–P9) |
| **P1–P9** | NGRBC principles (Ethics, Sustainability, Employees, Stakeholders, Human rights, Environment, Public policy, Inclusive growth, Customers) |
| **Datapoint** | One disclosure field; 337 across the BRSR form |
| **Core vs. Leadership** | Mandatory minimum (Core) vs. aspirational extra disclosures (Leadership) |
| **XBRL** | eXtensible Business Reporting Language — structured filing format SEBI accepts |
| **ESRS / GRI / TCFD** | Other ESG reporting frameworks we cross-map BRSR fields to |
| **NIFTY 50** | India's top-50 stock index — our benchmark cohort |
| **Tenant / Org** | A customer company; users belong to one org via `org_members` |
| **Worker** | Same backend image, run with `python -m app.worker`; polls a Supabase queue table for long-running jobs |

---

## Contact

- Owner: @ydvikasiitkgp-arch
- Issues: <https://github.com/ydvikasiitkgp-arch/filebrsr/issues>
- Production: <https://www.filebrsr.com>
