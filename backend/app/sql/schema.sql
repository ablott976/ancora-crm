CREATE SCHEMA IF NOT EXISTS ancora_crm;

-- Service catalog (what Ancora offers)
CREATE TABLE ancora_crm.service_catalog (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    default_monthly_price DECIMAL(10,2),
    default_setup_price DECIMAL(10,2),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clients
CREATE TABLE ancora_crm.clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,   -- URL-friendly identifier
    contact_name VARCHAR(200),
    contact_email VARCHAR(200),
    contact_phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    business_type VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) DEFAULT 'active',
    onboarding_date DATE,
    offboarding_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Client <-> Service assignments
CREATE TABLE ancora_crm.client_services (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES ancora_crm.clients(id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES ancora_crm.service_catalog(id),
    monthly_price DECIMAL(10,2),
    setup_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'active',
    started_at DATE,
    ended_at DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, service_id)
);

-- Invoices (uploaded PDFs analyzed by AI)
CREATE TABLE ancora_crm.invoices (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES ancora_crm.clients(id) ON DELETE CASCADE,
    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,
    amount DECIMAL(10,2),
    tax_amount DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'EUR',
    status VARCHAR(20) DEFAULT 'pending',
    concept TEXT,
    file_path VARCHAR(500),
    file_name VARCHAR(200),
    ai_extracted_data JSONB,
    ai_confidence DECIMAL(3,2),
    payment_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Data

INSERT INTO ancora_crm.service_catalog (name, description, default_monthly_price, default_setup_price, category, is_active) VALUES
('CRM Mensual', 'Suscripcion base de gestion comercial.', 99.00, 0.00, 'crm', true),
('Soporte Operativo', 'Acompanamiento operativo y mantenimiento.', 49.00, 0.00, 'operations', true)
ON CONFLICT DO NOTHING;
