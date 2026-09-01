-- =====================================================================
-- Gestor360 — Supabase / PostgreSQL schema
-- Execute this once in Supabase Dashboard → SQL Editor.
-- Safe to re-run: everything uses IF NOT EXISTS.
-- =====================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.companies (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT        NOT NULL DEFAULT '',   -- URL-safe slug (login step 1)
    password_hash   TEXT        NOT NULL DEFAULT '',   -- bcrypt hash of company password
    owner_id        TEXT        NOT NULL DEFAULT '',   -- user_id of the owner
    name            TEXT        NOT NULL DEFAULT '',
    cnpj            TEXT        NOT NULL DEFAULT '',
    ie              TEXT        NOT NULL DEFAULT '',
    address         TEXT        NOT NULL DEFAULT '',
    phone           TEXT        NOT NULL DEFAULT '',
    email           TEXT        NOT NULL DEFAULT '',
    logo_data_url   TEXT        NOT NULL DEFAULT '',
    stock_enabled   BOOLEAN     NOT NULL DEFAULT FALSE,
    pending_setup   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Unique code only when non-empty (allows multiple pending_setup empresas).
CREATE UNIQUE INDEX IF NOT EXISTS companies_code_unique
    ON public.companies (code) WHERE code <> '';

CREATE TABLE IF NOT EXISTS public.users (
    user_id                TEXT        PRIMARY KEY,          -- e.g. user_ab12cd34ef56
    company_id             UUID        NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    email                  TEXT        NOT NULL DEFAULT '',
    name                   TEXT        NOT NULL DEFAULT '',
    username               TEXT        NOT NULL DEFAULT '',
    password_hash          TEXT        NOT NULL DEFAULT '',
    auth_provider          TEXT        NOT NULL DEFAULT 'email',
    role                   TEXT        NOT NULL DEFAULT 'vendedor'
                                        CHECK (role IN ('owner','gerente','vendedor')),
    picture                TEXT        NOT NULL DEFAULT '',
    must_change_password   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS users_company_username_unique
    ON public.users (company_id, LOWER(username)) WHERE username <> '';
CREATE INDEX IF NOT EXISTS users_email_idx ON public.users (LOWER(email));
CREATE INDEX IF NOT EXISTS users_company_idx ON public.users (company_id);

CREATE TABLE IF NOT EXISTS public.clients (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id   UUID        NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL DEFAULT '',
    document     TEXT        NOT NULL DEFAULT '',
    ie           TEXT        NOT NULL DEFAULT '',
    email        TEXT        NOT NULL DEFAULT '',
    phone        TEXT        NOT NULL DEFAULT '',
    cep          TEXT        NOT NULL DEFAULT '',
    street       TEXT        NOT NULL DEFAULT '',
    number       TEXT        NOT NULL DEFAULT '',
    complement   TEXT        NOT NULL DEFAULT '',
    district     TEXT        NOT NULL DEFAULT '',
    city         TEXT        NOT NULL DEFAULT '',
    state        TEXT        NOT NULL DEFAULT '',
    address      TEXT        NOT NULL DEFAULT '',
    notes        TEXT        NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS clients_company_idx ON public.clients (company_id);
CREATE INDEX IF NOT EXISTS clients_company_name_idx ON public.clients (company_id, LOWER(name));

CREATE TABLE IF NOT EXISTS public.products (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID        NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    code          TEXT        NOT NULL DEFAULT '',
    description   TEXT        NOT NULL DEFAULT '',
    price         NUMERIC(14,2) NOT NULL DEFAULT 0,
    cost_price    NUMERIC(14,2) NOT NULL DEFAULT 0,
    stock         NUMERIC(14,3) NOT NULL DEFAULT 0,
    unit          TEXT        NOT NULL DEFAULT 'UN',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS products_company_code_unique
    ON public.products (company_id, code) WHERE code <> '';
CREATE INDEX IF NOT EXISTS products_company_idx ON public.products (company_id);

CREATE TABLE IF NOT EXISTS public.documents (
    id                        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                UUID        NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    doc_type                  TEXT        NOT NULL DEFAULT 'orcamento'
                                            CHECK (doc_type IN ('orcamento','venda')),
    number                    INTEGER     NOT NULL DEFAULT 0,
    client_id                 UUID        NOT NULL REFERENCES public.clients(id) ON DELETE RESTRICT,
    lines                     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    payments                  JSONB       NOT NULL DEFAULT '[]'::jsonb,
    global_discount_pct       NUMERIC(6,2)  NOT NULL DEFAULT 0,
    global_discount_amount    NUMERIC(14,2) NOT NULL DEFAULT 0,
    notes                     TEXT        NOT NULL DEFAULT '',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until               TIMESTAMPTZ NULL,
    converted_from            UUID        NULL,
    status                    TEXT        NOT NULL DEFAULT 'ativo',
    created_by                TEXT        NOT NULL DEFAULT ''  -- users.user_id (no FK to keep flexible)
);
CREATE INDEX IF NOT EXISTS documents_company_created_idx
    ON public.documents (company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS documents_company_type_idx
    ON public.documents (company_id, doc_type);
CREATE INDEX IF NOT EXISTS documents_client_idx ON public.documents (client_id);
CREATE INDEX IF NOT EXISTS documents_created_by_idx ON public.documents (created_by);
CREATE UNIQUE INDEX IF NOT EXISTS documents_company_type_number_unique
    ON public.documents (company_id, doc_type, number) WHERE number > 0;

CREATE TABLE IF NOT EXISTS public.counters (
    company_id   UUID        NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    doc_type     TEXT        NOT NULL CHECK (doc_type IN ('orcamento','venda')),
    value        INTEGER     NOT NULL DEFAULT 0,
    PRIMARY KEY (company_id, doc_type)
);

-- ---------------------------------------------------------------------
-- Row Level Security (defense in depth)
--
-- Our FastAPI backend connects with the SERVICE_ROLE key which BYPASSES RLS.
-- These policies ensure that ANY connection using the anon key (e.g. if
-- the anon key ever leaks into the browser) can read/write NOTHING.
-- Business-level tenant isolation is enforced in the backend via
-- `WHERE company_id = $1` on every query.
-- ---------------------------------------------------------------------

ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.counters  ENABLE ROW LEVEL SECURITY;

-- Force RLS also for owners of the table (extra strict).
ALTER TABLE public.companies FORCE ROW LEVEL SECURITY;
ALTER TABLE public.users     FORCE ROW LEVEL SECURITY;
ALTER TABLE public.clients   FORCE ROW LEVEL SECURITY;
ALTER TABLE public.products  FORCE ROW LEVEL SECURITY;
ALTER TABLE public.documents FORCE ROW LEVEL SECURITY;
ALTER TABLE public.counters  FORCE ROW LEVEL SECURITY;

-- Drop any pre-existing policies so this script is idempotent.
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT policyname, tablename FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('companies','users','clients','products','documents','counters')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', r.policyname, r.tablename);
  END LOOP;
END $$;

-- Deny everything for anon/authenticated Supabase roles.
-- (service_role bypasses RLS automatically — backend still has full access.)
CREATE POLICY companies_no_public   ON public.companies FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY users_no_public       ON public.users     FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY clients_no_public     ON public.clients   FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY products_no_public    ON public.products  FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY documents_no_public   ON public.documents FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY counters_no_public    ON public.counters  FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);

-- ---------------------------------------------------------------------
-- Helper: atomic counter increment (used by next_doc_number)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.next_doc_number(p_company UUID, p_doc_type TEXT)
RETURNS INTEGER AS $$
DECLARE new_value INTEGER;
BEGIN
    INSERT INTO public.counters (company_id, doc_type, value)
    VALUES (p_company, p_doc_type, 1)
    ON CONFLICT (company_id, doc_type)
    DO UPDATE SET value = public.counters.value + 1
    RETURNING value INTO new_value;
    RETURN new_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
