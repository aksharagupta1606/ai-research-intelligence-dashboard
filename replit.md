# AI Research Intelligence Dashboard

A Streamlit research workspace for exploring papers, analyzing text and PDFs, comparing studies, and viewing collection-level trends.

## Run & Operate

- `streamlit run app.py --server.address 0.0.0.0 --server.port 5000 --server.headless true --browser.gatherUsageStats false` — run the research dashboard
- `uvicorn api.routes:app --host 0.0.0.0 --port 8000` — run the research REST API
- `python scripts/seed_database.py` — add demo papers to the SQLite database
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Optional env: `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, `OPENALEX_MAILTO`, `MAX_UPLOAD_MB`; SQLite is the default.

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `app.py` — Streamlit startup and navigation
- `pages/` — dashboard page renderers
- `services/` — NLP, AI fallback, PDF, research API, and analytics logic
- `database/` — SQLAlchemy schema, database connection, and demo data
- `api/routes.py` — standalone FastAPI service
- `README.md` — setup, features, endpoint list, and limitations

## Architecture decisions

- The dashboard and API share the same SQLAlchemy database and local SQLite file by default.
- Local NLP is the default; no AI credentials are required for core features.
- The example records and their citation counts are illustrative, and gap signals are explicitly tentative.

## Product

- Search and filter a local paper collection or optionally search OpenAlex.
- Analyze pasted text and readable PDF text with local NLP or an optional AI provider.
- Review trends, author activity, paper comparisons, saved papers, and tentative gap signals.

## User preferences

-

## Gotchas

- Scanned PDFs need OCR; this app detects the lack of selectable text but does not perform OCR.
- Run `python scripts/seed_database.py` to seed or top up the database.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
- See `README.md` for the Python application's setup and limitations.
