# AI Support Desk

Vue 3 form -> FastAPI -> PostgreSQL. Each submitted request is analyzed synchronously by an
OpenAI-compatible LLM, which returns a category, priority, short summary and reply draft.

[Скриншот](image.png)

## Run

```bash
cp .env.example .env      # set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
docker compose up --build
```

- Frontend: http://localhost:8010
- API docs: http://localhost:8000/docs

## API

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/tickets` | Create ticket, store it, run LLM analysis |
| GET | `/api/tickets` | List (filters: `category`, `priority`, `status`, `limit`, `offset`) |
| GET | `/api/tickets/{id}` | Get one ticket |
| POST | `/api/tickets/{id}/reanalyze` | Re-run analysis (e.g. after a failure) |
| GET | `/api/llm/check` | Send a sample ticket to the LLM; returns `ok`, `error`, `http_status`, `raw_response`, `content`, `parsed` (200 if OK, 502 otherwise) |
| GET | `/api/health` | Health check |

If the LLM call fails, the ticket is still saved with `status=failed` and the error text.

## Tests

```bash
cd backend && pip install -r requirements.txt && pytest
```
