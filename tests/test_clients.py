async def test_get_clients_returns_rows(client, admin_headers, mock_db):
    clients = [
        {
            "id": 1,
            "name": "Acme",
            "slug": "acme",
            "contact_name": "Ana",
            "contact_email": "ana@example.com",
            "contact_phone": "600000000",
            "address": "Main St",
            "city": "Madrid",
            "business_type": "agency",
            "notes": None,
            "status": "active",
            "onboarding_date": None,
            "offboarding_date": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
    ]

    async def fetch_handler(query, *args):
        assert "FROM ancora_crm.clients" in query
        return clients

    mock_db.fetch_handler = fetch_handler

    response = await client.get("/api/clients", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == clients


async def test_add_client_service_returns_created_row(client, admin_headers, mock_db):
    created = {
        "id": 10,
        "client_id": 1,
        "service_id": 2,
        "monthly_price": 120.0,
        "setup_price": 30.0,
        "status": "active",
        "started_at": None,
        "ended_at": None,
        "notes": None,
        "created_at": "2025-01-01T00:00:00Z",
    }

    async def fetchrow_handler(query, *args):
        assert "INSERT INTO ancora_crm.client_services" in query
        assert args == (1, 2, 120.0, 30.0)
        return created

    mock_db.fetchrow_handler = fetchrow_handler

    response = await client.post(
        "/api/clients/1/services",
        json={"service_id": 2, "monthly_price": 120, "setup_price": 30},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == 10

