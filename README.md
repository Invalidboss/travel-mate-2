# travel-mate-2

Travel expenses schema and data-layer implementation for SQLite/PostgreSQL.

## What's included

- SQL migrations for both databases:
  - `migrations/sqlite/001_initial_schema.sql`
  - `migrations/postgresql/001_initial_schema.sql`
- Data model entities:
  - `Trip`
  - `ExpenseItem`
  - `Receipt`
  - `AllowanceCalculation`
  - `Reimbursement`
  - `Project` and `Customer` dimensions
- Repository layer (`src/travel_mate/repositories.py`) for persistence operations.
- Service layer (`src/travel_mate/services.py`) with ownership-aware update flow:
  - OCR updates can write fields unless a manual correction owns them.
  - Manual corrections always take ownership and block later OCR writes for those fields.

## Running tests

```bash
python -m pytest -q
```
