CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE patients (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name  TEXT NOT NULL,
    dob        DATE NOT NULL,
    phone      TEXT NOT NULL,
    email      TEXT NOT NULL,
    sms_opt_in BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id          UUID REFERENCES patients(id),
    conversation_state  JSONB NOT NULL DEFAULT '[]',
    appointment_state   JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE providers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    specialty  TEXT NOT NULL,
    body_parts TEXT[] NOT NULL,
    bio        TEXT
);

CREATE TABLE availability (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES providers(id),
    slot_time   TIMESTAMPTZ NOT NULL,
    is_booked   BOOLEAN DEFAULT FALSE
);

CREATE TABLE appointments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id  UUID REFERENCES patients(id),
    provider_id UUID REFERENCES providers(id),
    slot_time   TIMESTAMPTZ NOT NULL,
    reason      TEXT,
    status      TEXT DEFAULT 'confirmed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
