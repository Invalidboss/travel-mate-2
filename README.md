# travel-mate-2

Travel expense reporting prototype with backend report endpoints and dashboard pages.

## Backend endpoints

- `GET /reports/expenses-over-time` with query filters: `startDate`, `endDate`, `customer`, `project`, `status`, and `granularity=month|quarter`.
- `GET /reports/by-project` with query filters: `startDate`, `endDate`, `customer`, `project`, `status`.
- `GET /reports/open-reimbursements` with query filters: `startDate`, `endDate`, `customer`, `project`, `status`.
- `POST /trips/{id}/reimbursements` with JSON body `{ "amount": number, "date"?: string, "note"?: string }`.

Implemented in `backend/src/server.ts` and in-memory data in `backend/src/data.ts`.

## Frontend pages

- `frontend/src/pages/Dashboard.tsx`
  - Time-series totals by month/quarter.
  - Breakdown by customer/project/category.
  - Shared filters by date range, customer, project, status.
- `frontend/src/pages/Reimbursements.tsx`
  - Open reimbursement list (expected minus paid-back amounts).
  - Record reimbursement payback events by trip.
  - Shared filters by date range, customer, project, status.
