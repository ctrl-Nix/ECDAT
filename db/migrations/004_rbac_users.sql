-- ECDAT RBAC migration: user identity and role-based access control.
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL,
    organization_id TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT now(),
    last_login_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);