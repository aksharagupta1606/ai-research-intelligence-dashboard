# AI Research Intelligence Dashboard

An interactive research-analysis workspace for searching papers, exploring publication patterns, comparing studies, analyzing paper text and PDFs, and generating tentative research-gap signals.

> Demo data is illustrative. Sample paper metadata and citation counts are not claims about real publications. Potential research gaps require expert validation.

## Problem

Researchers often need to move between paper-search sites, spreadsheets, PDFs, and separate analysis tools just to understand a literature area. This dashboard brings paper metadata, lightweight NLP, comparison, and collection-level charts into one local workspace.

## What it does

- Research Explorer searches the local library, filters by topic, author, keyword, year, and citation range, and can search OpenAlex.
- Paper Analyzer produces extractive summaries, TF-IDF keywords, topic labels, methodology cues, and tentative gaps.
- PDF Analyzer extracts text from one or more PDFs, stores extracted text and metadata in SQLite, and analyzes readable documents.
- Research Trends shows filtered publication, topic, keyword, author, and citation charts.
- Research Gap Finder surfaces underrepresented topics and topic combinations with evidence and cautious language.
- Compare Papers compares 2–4 papers with a TF-IDF/cosine similarity heatmap and common/unique terms.
- Author Intelligence summarizes publications, topics, citations, and co-author connections.
- Saved Research persists a reading shortlist.
- Research Question Generator creates five topic-based starting questions.
- FastAPI exposes REST-style routes for search, analysis, upload, trends, save/unsave, and comparison.

## Technology

- Python 3.11+
- Streamlit
- SQLite + SQLAlchemy ORM
- Pandas, NumPy, Plotly
- Scikit-learn TF-IDF and cosine similarity
- PyMuPDF for PDF text extraction
- FastAPI, Pydantic, and Uvicorn
- OpenAlex public works API (optional)
- OpenAI-compatible API (optional)

## Architecture

```text
Researcher
  ├── Streamlit dashboard (app.py)
  │     └── Modular page renderers
  └── FastAPI REST service (api/routes.py)
          ↓
Application services
  ├── NLP and optional AI provider
  ├── Research API and PDF processing
  └── Analytics, paper library, and recommendations
          ↓
SQLAlchemy ORM
          ↓
SQLite (data/research.db by default)
```

The local NLP pipeline is the default. An AI API key is optional and is never required for the demo or core analysis. OpenAlex searches require an internet connection; the local collection remains available offline.

## Project structure

```text
app.py
api/                 FastAPI routes and Pydantic schemas
assets/style.css     Streamlit dashboard styling
config/              Environment-backed settings
database/             SQLAlchemy models, connection, demo seed
pages/                Streamlit page renderers
scripts/              Database setup scripts
services/             NLP, AI, PDF, OpenAlex, analytics, and library logic
utils/                Logging and text helpers
data/                 SQLite database and generated sample_data.csv
uploads/              Reserved for local upload files
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_database.py
streamlit run app.py --server.headless true --browser.gatherUsageStats false
```

The dashboard also creates the database and seeds demo records on first launch if the database is empty. The seed command is safe to run again: it adds only papers that are not already present.

To expose the app on a specific host/port:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 5000 --server.headless true --browser.gatherUsageStats false
```

### FastAPI

Run the REST API separately:

```bash
uvicorn api.routes:app --host 0.0.0.0 --port 8000
```

Open `/docs` on the API port for interactive OpenAPI documentation. The API and Streamlit app share the same SQLAlchemy database.

## Environment variables

Copy `.env.example` to `.env` if you want to configure optional integrations.

| Variable | Purpose | Default |
| --- | --- | --- |
| `AI_API_KEY` | Optional OpenAI-compatible provider credential | Empty; local NLP fallback |
| `AI_BASE_URL` | OpenAI-compatible API base URL | `https://api.openai.com/v1` |
| `AI_MODEL` | Model identifier accepted by that API | `gpt-4o-mini` |
| `RESEARCH_DATABASE_URL` | Optional SQLAlchemy database URL override | `sqlite:///data/research.db` |
| `OPENALEX_MAILTO` | Optional OpenAlex polite-pool contact | Empty |
| `MAX_UPLOAD_MB` | Maximum accepted PDF size | `25` |

Do not commit `.env`. The app never displays or logs API credentials.

## Database

SQLAlchemy creates the schema automatically. The SQLite database is stored at `data/research.db` by default.

Core tables: `papers`, `authors`, `topics`, `keywords`, their paper association tables, `paper_analysis`, `saved_papers`, and `uploaded_documents`.

To seed or top up the illustrative sample records:

```bash
python scripts/seed_database.py
```

The script also writes `data/sample_data.csv`.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service status |
| GET | `/api/papers` | Paginated papers with optional text/topic/author/year filters |
| GET | `/api/papers/{id}` | Paper details and stored analyses |
| GET | `/api/search?q=...` | Search paper titles and abstracts |
| GET | `/api/topics` | Topics and paper counts |
| GET | `/api/authors` | Authors and publication counts |
| GET | `/api/trends` | Publications-by-year and topic counts |
| POST | `/api/analyze` | Analyze submitted research text |
| POST | `/api/upload` | Extract and store a PDF |
| POST | `/api/papers/{id}/save` | Save a paper |
| DELETE | `/api/papers/{id}/save` | Remove a paper from saved research |
| POST | `/api/compare` | Compare 2–4 paper IDs |

## NLP and AI approach

Local analysis cleans and tokenizes text, removes stopwords, ranks terms with TF-IDF, scores topics using transparent keyword rules, selects representative sentences for an extractive summary, and calculates cosine similarity between paper text. Methodology, dataset, limitations, and future-work cues are found with explainable text rules.

When `AI_API_KEY` is configured, `services/ai_service.py` attempts an OpenAI-compatible chat-completions request. A missing key or failed request falls back to local NLP. AI output is not treated as verified scientific fact.

## PDF handling

PyMuPDF extracts selectable text. Invalid, oversized, password-protected, or unreadable PDFs produce friendly warnings. Image-only/scanned PDFs are identified as requiring OCR; OCR is not included. Extracted text and upload metadata are stored in the local database; uploaded binaries are not retained.

## Data and research-gap limitations

- The included 30 papers are illustrative demo records; their citation counts are sample values.
- OpenAlex availability depends on network access and its public service.
- PDF analysis depends on selectable text and can miss tables, figures, equations, and document layout.
- NLP topic and section extraction is heuristic, not a substitute for full-text review.
- Gap signals describe only the papers in the current collection and are not proof of a scientific gap.
- Similarity reflects word/phrase overlap in titles and abstracts, not scientific quality or novelty.
- This starter app has no multi-user authentication or role separation; use it as a local/single-user research workspace.

## Presentation notes

### Short college-project explanation

The AI Research Intelligence Dashboard helps researchers organize and analyze scientific literature in one place. It combines a Streamlit interface with a SQLite database, uses local NLP techniques to summarize and compare papers, and provides interactive charts for publications, topics, keywords, citations, and authors. Researchers can also upload PDFs, search OpenAlex, save papers, and review tentative research gaps. The system works without a paid AI key because it has a local NLP fallback.

### 60-second presentation

“My project is the AI Research Intelligence Dashboard, a research-analysis platform built with Python and Streamlit. It helps users search research papers, upload PDFs, analyze paper text, compare studies, and explore publication trends. The system stores paper and author data in SQLite through SQLAlchemy, while Pandas and Plotly power the interactive analytics. For text analysis, it uses TF-IDF keyword extraction, extractive summaries, topic matching, and cosine similarity. An optional OpenAI-compatible service can be enabled, but the application remains useful without an API key. OpenAlex search can add current research metadata when the internet is available. The gap finder highlights underrepresented themes only within the available collection and clearly asks researchers to validate any conclusion with domain experts.”

## Future enhancements

- OCR for scanned PDFs and layout-aware extraction for tables and figures.
- Authentication, shared research groups, and per-user libraries.
- More scholarly sources and richer bibliographic metadata.
- Citation graph and co-citation analysis.
- Expert-reviewed gap validation and audit trails.
- Background jobs for large document collections.

## Screenshots

Add screenshots of the dashboard, trends, comparison, and PDF analysis pages here.