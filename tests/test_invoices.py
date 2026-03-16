async def test_get_invoices_filters_by_client(client, admin_headers, mock_db):
    invoices = [
        {
            "id": 5,
            "client_id": 1,
            "invoice_number": "INV-1",
            "invoice_date": "2025-01-01",
            "due_date": "2025-01-15",
            "amount": 100.0,
            "tax_amount": 21.0,
            "total_amount": 121.0,
            "currency": "EUR",
            "status": "pending",
            "concept": "Monthly CRM",
            "file_path": None,
            "file_name": None,
            "ai_extracted_data": None,
            "ai_confidence": None,
            "payment_date": None,
            "notes": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
    ]

    async def fetch_handler(query, *args):
        assert "WHERE client_id = $1" in query
        assert args == (1,)
        return invoices

    mock_db.fetch_handler = fetch_handler

    response = await client.get("/api/invoices?client_id=1", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == invoices


async def test_delete_invoice_returns_success_message(client, admin_headers, mock_db):
    async def fetchrow_handler(query, *args):
        assert "DELETE FROM ancora_crm.invoices" in query
        assert args == (5,)
        return {"id": 5}

    mock_db.fetchrow_handler = fetchrow_handler

    response = await client.delete("/api/invoices/5", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {"message": "Invoice deleted"}
