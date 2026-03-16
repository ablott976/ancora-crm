async def test_get_services_returns_catalog(client, admin_headers, mock_db):
    services = [
        {
            "id": 2,
            "name": "CRM Mensual",
            "description": "Suscripcion base",
            "default_monthly_price": 99.0,
            "default_setup_price": 0.0,
            "category": "crm",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
        }
    ]

    async def fetch_handler(query, *args):
        assert "FROM ancora_crm.service_catalog" in query
        return services

    mock_db.fetch_handler = fetch_handler

    response = await client.get("/api/services", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == services


async def test_create_service_returns_created_row(client, admin_headers, mock_db):
    created = {
        "id": 3,
        "name": "Soporte Operativo",
        "description": "Acompanamiento",
        "default_monthly_price": 49.0,
        "default_setup_price": 0.0,
        "category": "operations",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
    }

    async def fetchrow_handler(query, *args):
        assert "INSERT INTO ancora_crm.service_catalog" in query
        return created

    mock_db.fetchrow_handler = fetchrow_handler

    response = await client.post(
        "/api/services",
        json={
            "name": "Soporte Operativo",
            "description": "Acompanamiento",
            "default_monthly_price": 49,
            "default_setup_price": 0,
            "category": "operations",
            "is_active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Soporte Operativo"

