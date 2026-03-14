# Test Suite Specification - Ancora CRM Plugins

## Architecture
- FastAPI app at app/main.py with lifespan that registers plugins
- PostgreSQL via asyncpg (app/database.py)
- Auth: JWT tokens, admin password from settings.admin_password
- Plugin routes mounted at prefix "/api/chatbot" 
- All dashboard routes require Bearer token auth
- Chatbot webhook at POST /api/chatbot/webhook/whatsapp (no auth)

## Test Strategy
Use pytest + httpx.AsyncClient with FastAPI's TestClient pattern.
Mock the database with asyncpg-stubs or a real test DB connection.
Use conftest.py fixtures for: app client, auth token, mock db.

## CRITICAL: Database Mocking
Since we can't connect to prod DB in tests, create mock fixtures that:
1. Use asyncpg mock or sqlite fallback
2. OR better: use the REAL production DB endpoint for integration tests
   - DB URL: postgresql://postgres:060322Tanit@144.91.110.134:5432/ancora_clients
   - Use a test schema (ancora_crm_test) to avoid touching production data
   - Run on_install for each plugin to create tables in test schema

## Plugins to Test (13 total)

### Level 0 - Core
1. **bookings** - Routes: /api/chatbot/bookings, Tools: 6 Gemini tools
2. **reminders** - Routes: /api/chatbot/reminders

### Level 1 - No dependencies  
3. **closures** - Routes: /api/chatbot/closures, Tools: check_closures, list_upcoming_closures
4. **daily_menus** - Routes: /api/chatbot/daily_menus, Tools: get_todays_menu, get_menu_by_date
5. **broadcasts** - Routes: /api/chatbot/broadcasts (campaigns, recipients, send-log)
6. **instagram_dm** - Routes: /api/chatbot/instagram-dm (config, conversations, messages)
7. **advanced_crm** - Routes: /api/chatbot/crm, Tools: lookup_customer, get_customer_history
8. **audio_transcription** - Routes: /api/chatbot/audio (transcriptions, stats)
9. **restaurant_bookings** - Routes: /api/chatbot/restaurant, Tools: 4 tools
10. **owner_agent** - Routes: /api/chatbot/owner, Tools: get_business_summary

### Level 2 - With dependencies
11. **consent_forms** - Routes: /api/chatbot/consents, Tools: check_pending_consents
12. **shift_view** - Routes: /api/chatbot/shifts, Tools: get_professional_agenda
13. **voice_agent** - Routes: /api/chatbot/voice (config, calls)

## Test Categories per Plugin

### A. Plugin Registration Tests
- Plugin is registered in PluginRegistry
- Plugin has correct id, name, version, dependencies
- Plugin returns valid router, tools, tool_handlers
- get_plugin_info() includes the plugin

### B. Schema Tests (on_install)
- on_install creates all required tables
- Tables have correct columns and constraints
- Indexes exist

### C. Service Layer Tests
- CRUD operations work correctly
- Edge cases: duplicate entries, not found, invalid data
- Business logic validation

### D. Dashboard Route Tests (require auth)
- GET list endpoints return 200 with valid token
- GET list endpoints return 401 without token
- POST create endpoints work
- PUT update endpoints work
- DELETE endpoints work
- Input validation (missing required fields)

### E. Chatbot Tool Tests (where applicable)
- Tool declarations are valid Gemini FunctionDeclaration objects
- Tool handlers return valid JSON strings
- Tool handlers handle missing/invalid args gracefully

### F. Integration Tests
- WhatsApp webhook processes messages and routes to correct instance
- Plugin tools are included in chatbot engine tool list
- System prompt sections are injected

## Auth for Tests
```python
# Get auth token
response = await client.post("/api/auth/login", data={"username": "admin", "password": "Ancora2026!"})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

## File Structure
```
tests/
  conftest.py          # Fixtures: app, client, auth, db
  test_plugin_registry.py  # Registration tests for all 13 plugins
  test_bookings.py
  test_reminders.py
  test_closures.py
  test_daily_menus.py
  test_broadcasts.py
  test_instagram_dm.py
  test_advanced_crm.py
  test_audio_transcription.py
  test_restaurant_bookings.py
  test_owner_agent.py
  test_consent_forms.py
  test_shift_view.py
  test_voice_agent.py
  test_webhook_integration.py  # WhatsApp webhook + plugin routing
  test_chatbot_tools.py        # All plugin tools declarations + handlers
```

## Running
```
cd /tmp/ancora-plugin-tests
pip install -r requirements-test.txt
pytest tests/ -v
```
