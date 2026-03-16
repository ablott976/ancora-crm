# Task: Complete Restaurant Bookings Plugin

## Context
ancora-crm is a multi-tenant SaaS CRM. The restaurant_bookings plugin has basic tools for the chatbot but the dashboard CRUD is incomplete, and it's missing the availability logic and reservation state machine from the Chilly's reference.

## Reference
- `reference/chillys_admin_routes.py` - Working admin routes with full reservation CRUD, confirm, cancel, noshow
- `/tmp/chillys-chatbot/services/reservations.py` - State machine, reservation creation with validation
- `/tmp/chillys-chatbot/services/availability.py` - Availability logic with zones/tables/slots

## What exists
- Schema: zones, tables, reservations (see `__init__.py`)
- 3 dashboard routes (list reservations, list zones, create zone)
- 7 services functions (basic CRUD)
- 5 chatbot tools
- Frontend page with basic list + zone creation

## What's needed

### 1. Backend: services.py - Complete reservation logic
Add/enhance:
a) `create_reservation(db, instance_id, ...)` - Create reservation with validation (check zone capacity, no double-booking)
b) `update_reservation(db, instance_id, reservation_id, **kwargs)` - Update reservation details
c) `confirm_reservation(db, instance_id, reservation_id)` - Set status to 'confirmada'
d) `cancel_reservation_dashboard(db, instance_id, reservation_id)` - Set status to 'cancelada', different from chatbot cancel (no WA notification)
e) `mark_noshow(db, instance_id, reservation_id)` - Set status to 'noshow'
f) `update_zone(db, instance_id, zone_id, **kwargs)` - Update zone details
g) `delete_zone(db, instance_id, zone_id)` - Deactivate zone
h) `create_table(db, instance_id, zone_id, table_number, seats)` - Create table in zone
i) `list_tables(db, instance_id, zone_id)` - List tables
j) `update_table(db, instance_id, table_id, **kwargs)` - Update table
k) `delete_table(db, instance_id, table_id)` - Deactivate table

State transitions: pending -> confirmada -> completada, pending -> cancelada, confirmada -> cancelada, confirmada -> noshow

### 2. Backend: routes.py - Full CRUD endpoints with correct auth
Change to dashboard auth pattern (like bookings/closures plugins):
- Remove self-prefix from router
- Use `require_plugin("restaurant_bookings")` + `get_current_chatbot_user`
- Add these endpoints under `/dashboard/{instance_id}/restaurant/`:
  - GET /reservations - list (with date filter)
  - POST /reservations - create
  - PUT /reservations/{id} - update
  - POST /reservations/{id}/confirm
  - POST /reservations/{id}/cancel
  - POST /reservations/{id}/noshow
  - GET /zones - list
  - POST /zones - create
  - PUT /zones/{id} - update
  - DELETE /zones/{id} - deactivate
  - GET /zones/{zone_id}/tables - list tables
  - POST /zones/{zone_id}/tables - create table
  - PUT /tables/{id} - update table
  - DELETE /tables/{id} - deactivate table

### 3. Frontend: RestaurantBookingsPage.tsx - Complete dashboard
Add:
- Reservation creation form (name, phone, date, time, party_size, zone, notes, allergies)
- Confirm/Cancel/NoShow action buttons on each reservation
- Tables management within zones (expandable zone -> tables list)
- Update API paths to use `dashboardPluginPath('restaurant', ...)`

### 4. Important constraints
- Multi-tenant: always filter by instance_id
- Follow the dashboard auth pattern from bookings plugin (require_plugin + get_current_chatbot_user)
- Don't break existing chatbot tools
- Use existing schema, don't add new tables
- State transitions should be validated

## Files to modify
- `backend/app/plugins/restaurant_bookings/services.py`
- `backend/app/plugins/restaurant_bookings/routes.py`
- `frontend/src/pages/plugins/RestaurantBookingsPage.tsx`
