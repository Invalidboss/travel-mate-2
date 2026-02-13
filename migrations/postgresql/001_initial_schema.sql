BEGIN;

CREATE TABLE customer (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  external_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project (
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES customer(id),
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE trip (
  id BIGSERIAL PRIMARY KEY,
  employee_name TEXT NOT NULL,
  project_id BIGINT NOT NULL REFERENCES project(id),
  customer_id BIGINT NOT NULL REFERENCES customer(id),
  start_datetime TIMESTAMPTZ NOT NULL,
  end_datetime TIMESTAMPTZ NOT NULL,
  is_domestic BOOLEAN NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'submitted', 'approved', 'rejected', 'paid')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (end_datetime >= start_datetime)
);

CREATE TABLE receipt (
  id BIGSERIAL PRIMARY KEY,
  file_path TEXT NOT NULL,
  ocr_text TEXT,
  vendor TEXT,
  receipt_date DATE,
  amount NUMERIC(12,2),
  confidence NUMERIC(5,4),
  processing_status TEXT NOT NULL CHECK (processing_status IN ('pending', 'processed', 'failed', 'verified')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE expense_item (
  id BIGSERIAL PRIMARY KEY,
  trip_id BIGINT NOT NULL REFERENCES trip(id) ON DELETE CASCADE,
  receipt_id BIGINT REFERENCES receipt(id),
  category TEXT NOT NULL,
  gross_amount NUMERIC(12,2) NOT NULL,
  net_amount NUMERIC(12,2),
  vat_amount NUMERIC(12,2),
  currency CHAR(3) NOT NULL,
  payment_method TEXT NOT NULL,
  receipt_link TEXT,
  booking_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE allowance_calculation (
  id BIGSERIAL PRIMARY KEY,
  trip_id BIGINT NOT NULL UNIQUE REFERENCES trip(id) ON DELETE CASCADE,
  allowance_per_day NUMERIC(12,2) NOT NULL,
  rule_version TEXT NOT NULL,
  meal_per_diem NUMERIC(12,2) NOT NULL,
  deduction_amount NUMERIC(12,2) NOT NULL,
  total_allowance NUMERIC(12,2) NOT NULL,
  total_payable NUMERIC(12,2) NOT NULL,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reimbursement (
  id BIGSERIAL PRIMARY KEY,
  trip_id BIGINT NOT NULL UNIQUE REFERENCES trip(id) ON DELETE CASCADE,
  expected_amount NUMERIC(12,2) NOT NULL,
  paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  paid_date DATE,
  open_amount NUMERIC(12,2) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE field_update_ownership (
  id BIGSERIAL PRIMARY KEY,
  entity_name TEXT NOT NULL,
  entity_id BIGINT NOT NULL,
  field_name TEXT NOT NULL,
  owner_source TEXT NOT NULL CHECK (owner_source IN ('ocr', 'manual', 'system')),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (entity_name, entity_id, field_name)
);

CREATE INDEX idx_trip_project_id ON trip(project_id);
CREATE INDEX idx_trip_customer_id ON trip(customer_id);
CREATE INDEX idx_expense_item_trip_id ON expense_item(trip_id);
CREATE INDEX idx_expense_item_receipt_id ON expense_item(receipt_id);
CREATE INDEX idx_receipt_processing_status ON receipt(processing_status);
CREATE INDEX idx_field_update_ownership_entity ON field_update_ownership(entity_name, entity_id);

COMMIT;
