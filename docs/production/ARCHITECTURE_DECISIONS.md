# Architecture Decisions

## 0. Scope reality — read this first

The execution prompt driving this workstream specifies 17 phases: a full frontend/backend/database rewrite, multi-tenant auth and RBAC, GPU benchmarking, a security threat model with adversarial testing, load testing, CI/CD, Docker production deployment, and a revised research paper — against a project that, per `INITIAL_AUDIT.md`, currently has no HTTP API, no database, no auth, runs on a single 16GB Apple Silicon laptop with no NVIDIA GPU, and has never had a real multi-user deployment or an actual second user. This is genuinely multi-week, multi-engineer scope. The prompt itself anticipates this ("If context limits or execution limits prevent completing everything in one session, create a detailed persistent execution log... continue from the repository state rather than starting over") — that is the mode this workstream operates in, not a claim that everything below is finished in one pass.

**What this document does:** makes the specific, reasoned architecture decisions needed to start building for real, scoped to what is actually defensible on this hardware and for this project's actual (single final-year-student, local-machine) usage pattern — rather than either (a) refusing to start, or (b) fabricating a full enterprise SaaS stack that is never run or verified. Every decision below is revisited if a later phase's real findings contradict it.

A persistent execution log tracking exactly what is done, in progress, and pending across all 17 phases lives at `docs/production/EXECUTION_LOG.md` — read that first in any future session continuing this work.

## 1. Deployment target: single-machine, secure-local-mode first

**Decision:** build for a single-machine deployment (the documented "secure single-user/local mode" the prompt explicitly asks for) as the primary, fully-built target. A multi-user mode is designed for and documented (data model has `workspace_id`/`owner_id` fields from day one, so it is not a retrofit), but its auth/RBAC enforcement layer is scoped as a near-term follow-up rather than built and load-tested this session.

**Why:** there is no current multi-user requirement, no deployed users, and no cloud account to deploy a multi-tenant system to. Building a full auth/RBAC/multi-tenant system that is never exercised by a second real user would produce exactly the "unverified claims" the prompt itself prohibits ("Do not claim something is production-ready, secure... unless you have actually verified it"). Designing the schema to support it later avoids a costly rewrite.

## 2. Backend: FastAPI, modular monolith

**Decision:** a single FastAPI service wrapping the existing `quimrag/` package as its core library (unchanged), exposing it over HTTP. Internally organized into clear modules (ingestion, retrieval, EAR, RVQ, admin) but deployed as one process, not separate microservices.

**Why:** the prompt's own guidance says "Prefer a modular monolith initially unless measured scale or isolation requirements justify separate services" — no such requirement exists here (single machine, no measured concurrent load). `quimrag/core.py`'s `QuIMRAG` class already has no Streamlit coupling, making it a clean library to wrap without modification.

## 3. Database: SQLite by default, Postgres+pgvector as a documented optional path

**Decision:** document and metadata persistence (documents, chunks, jobs, audit records) uses SQLite by default for local development and the single-machine deployment target, with a Postgres+pgvector Docker Compose profile provided and documented as the upgrade path for anyone who wants it (this satisfies the prompt's explicit request for a Postgres/pgvector option without forcing a database server onto a 16GB laptop for local single-user use).

**Why:** SQLite requires no separate server process, which matters materially on a 16GB RAM machine also running embedding models, a reranker, and potentially a local LLM via Ollama simultaneously. Vector search at this project's actual scale (hundreds to low thousands of documents, not millions) does not need pgvector's ANN indexing to perform acceptably — the existing in-memory cosine/BM25/RRF retrieval already measured at 36-40ms mean latency (`BASELINE_PERFORMANCE.md` §3) is not the bottleneck Postgres would need to solve. The schema is written to be portable to Postgres without redesign.

## 4. Frontend: a lightweight web UI now, Next.js path documented, Streamlit retained

**Decision:** retain the existing Streamlit app unmodified as the "research console" (exactly as the prompt allows: "Preserve the current Streamlit application as a research console or compatibility interface where appropriate"). Build a minimal, real, working web frontend against the new FastAPI backend for the core end-to-end workflow (upload → ingest → ask → cite → delete) as proof the API layer actually works end-to-end for a human in a browser, rather than committing this session's remaining budget to a full nine-page Next.js enterprise application that cannot be meaningfully built, wired to real data, AND verified in the time available.

**Why:** the prompt's own Phase 3 required product areas (Command Center, Document Library, Processing Studio, Ask QuIM, Retrieval Lab, Explainability, Benchmark & Evaluation, Administration, System Configuration) are, in combination, a multi-week frontend build on their own. Building a skeleton of all nine without wiring most of them to real backend data would violate the prompt's own explicit rule ("No fake statistics, dummy user activity, placeholder graphs... in production mode"). A smaller number of fully-real, fully-wired pages is more defensible than nine partially-fake ones.

## 5. GPU/acceleration: MPS-only, CUDA path documented but unverified

**Decision:** the existing MPS-aware code path (`quimrag/core.py::device_name()`) is the acceleration baseline, now actually benchmarked (`BASELINE_PERFORMANCE.md`). A CUDA execution path is written to the same device-abstraction interface and documented, but is explicitly marked unverified, since no NVIDIA GPU exists on this machine (`INITIAL_AUDIT.md` §4). No speedup is claimed for a code path that cannot be tested here.

## 6. Authentication: documented, minimal, not a full RBAC system this pass

**Decision:** the single-machine deployment target does not require authentication for its primary use case (one person, their own machine, their own documents). An optional API-key-based auth mechanism is implemented for the FastAPI service (since exposing an unauthenticated HTTP API on a shared network is a real risk even single-user), with the schema supporting future per-workspace roles. Full RBAC, SSO, and multi-tenant permission enforcement are explicitly scoped as follow-up work, not claimed as done.

## 7. What this session will actually build and verify, in priority order

1. FastAPI backend wrapping `quimrag/` (ingestion, retrieval, EAR, citation endpoints) — runnable, hit with real requests, verified end-to-end.
2. SQLite-backed document/chunk/job metadata store with a real migration.
3. A minimal web frontend for the upload → ask → cite → delete workflow, calling the real API.
4. Regression + integration tests for the new API layer, run and passing.
5. A Dockerfile/Compose update reflecting the new service(s), including the documented Postgres+pgvector profile.
6. Updated documentation reflecting what was actually built and verified vs. documented-but-not-built.

Everything else in the 17-phase prompt (full RBAC, load testing at scale, CI pipeline, GPU benchmarking beyond what's possible on this hardware, the full nine-page product surface, dataset download/acquisition for a new benchmark, the revised research paper) is tracked explicitly in `EXECUTION_LOG.md` as pending, with its own priority and rationale, rather than silently dropped or falsely marked complete.
