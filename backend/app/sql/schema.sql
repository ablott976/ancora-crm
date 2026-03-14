CREATE SCHEMA IF NOT EXISTS ancora_crm;

-- Service catalog (what Ancora offers)
CREATE TABLE ancora_crm.service_catalog (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,         -- e.g. "Chatbot WhatsApp", "Sistema Reservas"
    description TEXT,
    default_monthly_price DECIMAL(10,2),
    default_setup_price DECIMAL(10,2),
    category VARCHAR(50),               -- "chatbot", "reservas", "menu", "voice", "consentimientos", etc.
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
    business_type VARCHAR(100),          -- "restaurante", "tattoo_studio", etc.
    notes TEXT,
    status VARCHAR(20) DEFAULT 'active', -- active, inactive, suspended
    dashboard_url VARCHAR(500),          -- link to their deployed app
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
    monthly_price DECIMAL(10,2),         -- override per client
    setup_price DECIMAL(10,2),           -- override per client
    status VARCHAR(20) DEFAULT 'active', -- active, paused, cancelled
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
    status VARCHAR(20) DEFAULT 'pending', -- pending, paid, overdue, cancelled
    concept TEXT,                          -- extracted description
    file_path VARCHAR(500),               -- stored PDF path
    file_name VARCHAR(200),
    ai_extracted_data JSONB,              -- raw AI extraction
    ai_confidence DECIMAL(3,2),           -- 0.00-1.00
    payment_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chatbot Tables

CREATE TABLE ancora_crm.chatbot_instances (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES ancora_crm.clients(id),
    service_type VARCHAR(50) NOT NULL DEFAULT 'chatbot_whatsapp_basic',
    phone_number_id VARCHAR(50) NOT NULL UNIQUE, -- Meta phone number ID
    display_phone_number VARCHAR(20), -- The actual phone number displayed
    whatsapp_access_token TEXT NOT NULL, -- Meta access token for sending messages
    whatsapp_graph_url VARCHAR(200) DEFAULT 'https://graph.facebook.com/v19.0',
    google_api_key TEXT, -- Gemini API key (can use shared default)
    gemini_model VARCHAR(100) DEFAULT 'gemini-2.0-flash',
    gemini_temperature FLOAT DEFAULT 0.7,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ancora_crm.chatbot_business_info (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL UNIQUE REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    business_name VARCHAR(200),
    business_type VARCHAR(100), -- "restaurante", "clínica", "tattoo studio", etc.
    description TEXT, -- What the business does
    address TEXT,
    city VARCHAR(100),
    phone VARCHAR(20), -- Public business phone
    email VARCHAR(200),
    website VARCHAR(200),
    services_offered TEXT, -- Free text describing services/prices
    additional_info TEXT, -- Any extra info for the chatbot
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ancora_crm.chatbot_schedule (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    dia_semana INTEGER NOT NULL, -- 0=Monday, 6=Sunday
    hora_apertura VARCHAR(5) DEFAULT '09:00',
    hora_cierre VARCHAR(5) DEFAULT '18:00',
    abierto BOOLEAN DEFAULT true,
    UNIQUE(instance_id, dia_semana)
);

CREATE TABLE ancora_crm.chatbot_holidays (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    nombre VARCHAR(200),
    UNIQUE(instance_id, fecha)
);

CREATE TABLE ancora_crm.chatbot_prompts (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    filename VARCHAR(100) NOT NULL, -- 'system.txt' for main prompt
    content TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, filename)
);

CREATE TABLE ancora_crm.chatbot_dashboard_users (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin', -- only 'admin' for now
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, username)
);

CREATE TABLE ancora_crm.chatbot_contacts (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    phone VARCHAR(20) NOT NULL, -- WhatsApp number
    name VARCHAR(200), -- NULL if unknown
    email VARCHAR(200),
    address TEXT,
    notes TEXT,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, phone)
);

CREATE TABLE ancora_crm.chatbot_conversations (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    contact_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_contacts(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL, -- 'user' or 'model'
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_chatbot_conv_contact ON ancora_crm.chatbot_conversations(contact_id, created_at);
CREATE INDEX idx_chatbot_conv_instance ON ancora_crm.chatbot_conversations(instance_id, created_at);

-- Seed Data

-- Service Catalog (only plugin-based services)
INSERT INTO ancora_crm.service_catalog (name, description, default_monthly_price, default_setup_price, category, is_active) VALUES
('Chatbot WhatsApp Básico', 'Chatbot básico con IA que responde dudas sobre un negocio por WhatsApp', 49.00, 149.00, 'chatbot_whatsapp_basic', true)
ON CONFLICT DO NOTHING;
