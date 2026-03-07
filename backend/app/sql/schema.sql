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

-- Seed Data (MUST be included in schema.sql)

-- Service Catalog
INSERT INTO ancora_crm.service_catalog (name, description, default_monthly_price, default_setup_price, category) VALUES
('Chatbot WhatsApp', 'Chatbot inteligente para WhatsApp Business API con IA', 99.00, 250.00, 'chatbot'),
('Chatbot Instagram', 'Chatbot inteligente para Instagram Direct', 79.00, 200.00, 'chatbot'),
('Sistema de Reservas', 'Gestión de reservas con disponibilidad en tiempo real', 49.00, 150.00, 'reservas'),
('Gestión de Menús', 'Publicación y envío masivo de menús diarios por WhatsApp', 39.00, 100.00, 'menu'),
('Recordatorios Automáticos', 'Sistema de recordatorios por WhatsApp (citas, reservas)', 29.00, 50.00, 'recordatorios'),
('Consentimientos Digitales', 'Consentimientos informados digitales con firma electrónica', 39.00, 150.00, 'consentimientos'),
('Agente de Voz (VAPI)', 'Asistente telefónico con IA para reservas y consultas', 89.00, 300.00, 'voice'),
('Envío Masivo WhatsApp', 'Campañas y envíos masivos por WhatsApp', 49.00, 100.00, 'marketing');

-- Client: CHILLY'S
INSERT INTO ancora_crm.clients (name, slug, contact_phone, address, city, business_type, notes, status, dashboard_url, onboarding_date) VALUES
('CHILLY''S', 'chillys', '910719612', 'Calle de Sta. Ana, 16, 28860 Paracuellos de Jarama', 'Madrid', 'restaurante',
 'Restaurante-bar. Hamburguesas, tequeños, baos, cócteles. Rating 4.7 (162 reseñas). Terraza, perros OK, tronas. Solo cenas Ma-S 19:00-02:00 (L y D cerrado).',
 'active', 'https://n8n-chillys-chatbot.9kpuqs.easypanel.host', '2026-03-05');

-- Client: SEVEN SISTERS TATTOO
INSERT INTO ancora_crm.clients (name, slug, contact_name, address, city, business_type, notes, status, dashboard_url, onboarding_date) VALUES
('Seven Sisters Tattoo', 'seven-sisters', 'Raúl', NULL, 'Madrid', 'tattoo_studio',
 'Estudio de tatuajes. Artista principal: Raúl. Sistema completo: chatbot WA/IG, reservas, recordatorios, consentimientos digitales (Decreto 35/2005 CAM).',
 'active', 'https://n8n-sevensisters-chatbot.9kpuqs.easypanel.host', '2026-02-01');

-- CHILLY'S services
INSERT INTO ancora_crm.client_services (client_id, service_id, monthly_price, setup_price, status, started_at) VALUES
((SELECT id FROM ancora_crm.clients WHERE slug='chillys'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Chatbot WhatsApp'), 99.00, 250.00, 'active', '2026-03-05'),
((SELECT id FROM ancora_crm.clients WHERE slug='chillys'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Sistema de Reservas'), 49.00, 150.00, 'active', '2026-03-05'),
((SELECT id FROM ancora_crm.clients WHERE slug='chillys'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Gestión de Menús'), 39.00, 100.00, 'active', '2026-03-05'),
((SELECT id FROM ancora_crm.clients WHERE slug='chillys'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Agente de Voz (VAPI)'), 89.00, 300.00, 'active', '2026-03-05'),
((SELECT id FROM ancora_crm.clients WHERE slug='chillys'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Envío Masivo WhatsApp'), 49.00, 100.00, 'active', '2026-03-05');

-- SEVEN SISTERS services
INSERT INTO ancora_crm.client_services (client_id, service_id, monthly_price, setup_price, status, started_at) VALUES
((SELECT id FROM ancora_crm.clients WHERE slug='seven-sisters'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Chatbot WhatsApp'), 99.00, 250.00, 'active', '2026-02-01'),
((SELECT id FROM ancora_crm.clients WHERE slug='seven-sisters'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Chatbot Instagram'), 79.00, 200.00, 'active', '2026-02-01'),
((SELECT id FROM ancora_crm.clients WHERE slug='seven-sisters'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Sistema de Reservas'), 49.00, 150.00, 'active', '2026-02-01'),
((SELECT id FROM ancora_crm.clients WHERE slug='seven-sisters'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Recordatorios Automáticos'), 29.00, 50.00, 'active', '2026-02-01'),
((SELECT id FROM ancora_crm.clients WHERE slug='seven-sisters'), (SELECT id FROM ancora_crm.service_catalog WHERE name='Consentimientos Digitales'), 39.00, 150.00, 'active', '2026-02-01');
