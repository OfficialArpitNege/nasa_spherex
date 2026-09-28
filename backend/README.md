# SPHEREx Moving Object Explorer — Backend

FastAPI backend service for the **SPHEREx Moving Object Explorer** project.

## Quickstart

### Running the Server
```bash
uvicorn app.main:app --reload
```

### Running Tests
```bash
pytest
```

### Endpoints
- **Health Check**: `GET /api/health`
- **Swagger Documentation**: `GET /docs`
- **OpenAPI Schema**: `GET /openapi.json`
