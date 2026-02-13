# Travel Mate

Simple monorepo starter for creating trip expense reports.

## Structure

- `backend/`: FastAPI service for trip management, receipt upload, summary generation, and Excel export.
- `frontend/`: React + Vite single-page app for trip input and receipt uploads.
- `docker-compose.yml`: one-command local startup.

## Run locally

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs

## API endpoints

- `POST /trips`
- `POST /trips/{id}/receipts`
- `GET /trips/{id}/summary`
- `GET /trips/{id}/export.xlsx`
