# Project instructions

## Stack
- Python 3.12
- FastAPI
- SQLAlchemy 2
- PostgreSQL
- Vue 3
- pytest

## Backend rules
- Use async endpoints.
- Use Pydantic schemas.
- Do not access DB directly from routers.
- Business logic belongs in services.
- All public API endpoints must have tests.

## LLM rules
- Never trust raw LLM output.
- Validate all model responses with Pydantic.
- LLM provider must be isolated behind LLMService.
- Do not put API keys into source code.

## Development
- Run tests after backend changes.
- Do not modify database schema without creating a migration.
