CREATE TABLE IF NOT EXISTS transactions (
    id          TEXT PRIMARY KEY,
    date        DATE,
    value_date  DATE,
    bank        TEXT,
    type        TEXT,
    description TEXT,
    amount      NUMERIC(12, 2),
    category    TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
