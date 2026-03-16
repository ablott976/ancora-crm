# Task: Complete Broadcasts Plugin

## Context
ancora-crm is a multi-tenant SaaS CRM for WhatsApp chatbot clients. Each client has a `chatbot_instance` with its own WhatsApp credentials (access_token, phone_number_id) stored in `ancora_crm.chatbot_instances`.

The broadcasts plugin currently has basic CRUD but is missing the actual sending logic. The reference implementation from Chilly's chatbot (in `reference/chillys_broadcasts.py`) has the complete working version for a single-tenant app. We need to adapt it for multi-tenant.

## What exists
- Schema: `ancora_crm.plugin_broadcasts_campaigns`, `plugin_broadcasts_recipients`, `plugin_broadcasts_send_log` (see `__init__.py`)
- CRUD routes in `backend/app/plugins/broadcasts/routes.py`
- CRUD services in `backend/app/plugins/broadcasts/services.py`
- WhatsApp sending util in `backend/app/services/chatbot_whatsapp.py` (send_message function)
- Frontend page in `frontend/src/pages/plugins/BroadcastsPage.tsx`

## What's needed

### 1. Backend: services.py - Add sending logic
Add these functions to `backend/app/plugins/broadcasts/services.py`:

a) `resolve_audience(db, instance_id, campaign)` - Resolve target contacts based on campaign config:
   - `all`: all contacts with `opt_in_marketing=true` and no `opted_out_at`
   - `tags`: contacts matching ANY of `target_tags` (recipients table has `tags` array field)
   - Return list of dicts with `phone`, `name`

b) `send_campaign(db, instance_id, campaign_id)` - Execute a campaign:
   - Validate campaign exists and status is 'draft' or 'scheduled'
   - Set status to 'sending'
   - Get instance's WA credentials from `ancora_crm.chatbot_instances` (access_token=whatsapp_access_token, phone_number_id)
   - Resolve audience
   - For each recipient: send WA message using `chatbot_whatsapp.send_message`, log in `send_log`, rate limit with asyncio.sleep(0.05)
   - Update campaign totals (total_recipients, total_sent, total_delivered, total_failed)
   - Set status to 'sent'
   - Return summary dict

c) `check_scheduled_campaigns(db)` - Find campaigns where status='scheduled' and scheduled_at <= NOW(), send each one. This will be called by an external scheduler.

### 2. Backend: routes.py - Add send endpoint
Add `POST /campaigns/{instance_id}/{campaign_id}/send` endpoint that calls `send_campaign`.

### 3. Frontend: BroadcastsPage.tsx - Add send button
Add a "Send" button for draft/scheduled campaigns that calls the send endpoint. Show sending state and results.

### 4. Auth fix
Change routes.py to use the same pattern as closures/bookings:
- Import `get_current_chatbot_user` from `app.services.chatbot_auth` instead of `get_current_user` from `app.routes.auth`
- Use `require_plugin("broadcasts")` for instance_id validation
- Change route paths from `/campaigns/{instance_id}` to `/dashboard/{instance_id}/broadcasts/campaigns` (matching the bookings pattern)
- Update frontend to use `dashboardPluginPath('broadcasts/campaigns')` instead of `pluginRoutePath('broadcasts/campaigns/10')`

### 5. Add chatbot tools
Create `backend/app/plugins/broadcasts/tools.py` with Gemini function calling tools so the chatbot can:
- `check_broadcast_status`: Check if there are any active/scheduled campaigns
- `get_opt_in_count`: Return count of opted-in recipients

Register tools in `__init__.py`.

## Important constraints
- Multi-tenant: always filter by instance_id
- Get WA credentials from `ancora_crm.chatbot_instances` table (columns: `whatsapp_access_token`, `phone_number_id`)
- Use `app.services.chatbot_whatsapp.send_message(to, body, access_token, phone_number_id)` for sending
- Recipients phone format should include country code (e.g., "34612345678")
- Rate limit: asyncio.sleep(0.05) between sends (~20 msgs/sec)
- Don't break existing CRUD functionality
- Follow existing code patterns in the project (asyncpg via db dependency, no raw pool)

## Files to modify
- `backend/app/plugins/broadcasts/services.py` - Add send logic
- `backend/app/plugins/broadcasts/routes.py` - Add send endpoint + fix auth pattern
- `backend/app/plugins/broadcasts/__init__.py` - Register tools
- `backend/app/plugins/broadcasts/tools.py` - NEW: chatbot tools
- `frontend/src/pages/plugins/BroadcastsPage.tsx` - Add send button + fix API paths

## Reference files
- `reference/chillys_broadcasts.py` - Working single-tenant implementation
- `backend/app/plugins/bookings/routes.py` - Example of correct auth pattern
- `backend/app/services/chatbot_whatsapp.py` - WA send function
