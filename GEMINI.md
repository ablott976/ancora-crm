# GEMINI.md — Ancora CRM

## Project Overview
Ancora CRM is a client management dashboard for **Ancora Automations**, a small Spanish automation agency. It manages clients, their services, and invoices.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 18+ with Vite, TypeScript, TailwindCSS
- **Database**: PostgreSQL (schema `ancora_crm`)
- **Invoice Analysis**: AI-powered PDF extraction (Claude API via Anthropic SDK)
- **Auth**: Simple password-based login (single admin user, no registration)

## Architecture
```
ancora-crm/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app with lifespan
│   │   ├── config.py            # Settings (env-based)
│   │   ├── database.py          # asyncpg connection pool
│   │   ├── models/              # Pydantic models
│   │   ├── routes/
│   │   │   ├── auth.py          # Login/session
│   │   │   ├── clients.py       # CRUD clients
│   │   │   ├── services.py      # Service catalog + assignments
│   │   │   ├── invoices.py      # Upload, list, AI analysis
│   │   │   └── dashboard.py     # Stats/metrics
│   │   ├── services/
│   │   │   ├── invoice_analyzer.py  # AI PDF analysis
│   │   │   └── client_service.py
│   │   └── sql/
│   │       └── schema.sql       # Full DB schema
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      # Overview: active clients, MRR, pending invoices
│   │   │   ├── Clients.tsx        # Client list + CRUD
│   │   │   ├── ClientDetail.tsx   # Single client: info, services, invoices
│   │   │   ├── Invoices.tsx       # All invoices view
│   │   │   ├── Services.tsx       # Service catalog
│   │   │   └── Login.tsx
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Database Schema (PostgreSQL, schema `ancora_crm`)

```sql
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
```

## Seed Data (MUST be included in schema.sql)

```sql
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
```

## Frontend Design Requirements

### Visual Identity
- **Brand**: Ancora Automations — automation agency for Spanish SMBs
- **Aesthetic**: Dark theme, professional but modern. Think Linear/Vercel dashboard vibes.
- **Colors**: Dark slate background (#0f172a), accent blue (#3b82f6), success green (#22c55e), warm amber for warnings
- **Typography**: Use Google Fonts — something distinctive, NOT Inter/Roboto. Consider "Plus Jakarta Sans" or "Outfit" for headings, "DM Sans" for body.
- **Logo**: Text-only "Ancora" with an anchor ⚓ icon, placed in sidebar

### Layout
- **Sidebar navigation**: Dashboard, Clientes, Servicios, Facturas, Configuración
- **Top bar**: Page title + admin avatar/logout
- **Responsive**: Mobile-friendly but desktop-first

### Pages

**Dashboard (/):**
- Cards: Total Clients (active), MRR (sum of active monthly services), Pending Invoices, Total Revenue YTD
- Recent activity feed
- Client status overview (mini cards per client with their services as badges)

**Clients (/clients):**
- Table/card view with search and status filter
- Click to open ClientDetail
- "Nuevo Cliente" button → modal form

**Client Detail (/clients/:slug):**
- Client info (editable)
- Services section: assigned services with prices, toggle active/paused, add/remove
- Invoices section: list of invoices for this client, upload button
- Link to their dashboard (external)

**Invoices (/invoices):**
- All invoices table, filterable by client, status, date
- Upload invoice → select client → AI extracts data → review & confirm
- Status badges: pending (amber), paid (green), overdue (red)

**Services (/services):**
- Service catalog CRUD
- Default pricing management

### Key Interactions
- Invoice upload: drag & drop PDF → backend sends to AI → returns extracted fields → user reviews in modal → save
- Client status change: confirmation dialog
- Service assignment: dropdown of available services with price override option

## Backend Requirements

### API Endpoints
```
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/dashboard/stats

GET    /api/clients
POST   /api/clients
GET    /api/clients/:id
PUT    /api/clients/:id
DELETE /api/clients/:id (soft delete → status=inactive)

GET    /api/clients/:id/services
POST   /api/clients/:id/services
PUT    /api/clients/:id/services/:service_id
DELETE /api/clients/:id/services/:service_id

GET    /api/services (catalog)
POST   /api/services
PUT    /api/services/:id
DELETE /api/services/:id

GET    /api/invoices
GET    /api/invoices?client_id=X
POST   /api/invoices/upload  (multipart: PDF file + client_id)
PUT    /api/invoices/:id
DELETE /api/invoices/:id
GET    /api/invoices/:id/download (serve PDF)
POST   /api/invoices/:id/analyze (re-run AI analysis)
```

### Invoice AI Analysis
Use Anthropic's Claude API (anthropic Python SDK) to analyze uploaded invoice PDFs:
- Extract: invoice_number, date, due_date, amount, tax, total, concept/description
- Return confidence score
- Store raw extraction in `ai_extracted_data` JSONB field
- The user reviews and can edit before saving
- Environment variable: `ANTHROPIC_API_KEY`

### Configuration (environment variables)
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=<random-32-chars>
ADMIN_PASSWORD=Ancora2026!
ANTHROPIC_API_KEY=<key>
UPLOAD_DIR=/app/uploads
```

## Docker Setup
- `docker-compose.yml` with: backend, frontend (nginx serving built React), postgres
- Backend Dockerfile: Python 3.11-slim, uvicorn
- Frontend Dockerfile: Node build stage → nginx serve
- Uploads volume for invoice PDFs

## CRITICAL RULES
1. **Python 3.10 compatible** — use `Optional[X]` not `X | None`, `Union` not pipe syntax
2. **asyncpg** for database (NOT SQLAlchemy) — direct SQL queries
3. **No ORM** — write raw SQL, it's simpler and we control it
4. **Schema prefix** — ALL tables must use `ancora_crm.` prefix
5. **CORS** — allow all origins in dev (configurable)
6. **SPA routing** — backend serves frontend static files, catch-all returns index.html
7. **Error handling** — proper HTTP status codes, JSON error responses
8. **The app must be COMPLETE and WORKING** — not a skeleton. All CRUD operations, all pages, invoice upload + AI analysis, seed data.
