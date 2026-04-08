import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()


@pytest.mark.asyncio
async def test_create_customer(client: AsyncClient):
    response = await client.post(
        "/api/v1/customers",
        json={
            "name": "Test Customer",
            "code": "TEST001",
            "description": "Test customer for unit testing"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Customer"
    assert data["code"] == "TEST001"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_customers(client: AsyncClient):
    await client.post(
        "/api/v1/customers",
        json={"name": "Customer A", "code": "CUSTA", "description": "A"}
    )
    await client.post(
        "/api/v1/customers",
        json={"name": "Customer B", "code": "CUSTB", "description": "B"}
    )
    
    response = await client.get("/api/v1/customers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_create_server(client: AsyncClient):
    customer_response = await client.post(
        "/api/v1/customers",
        json={"name": "Server Test Customer", "code": "SrvTest"}
    )
    customer_id = customer_response.json()["id"]
    
    response = await client.post(
        "/api/v1/servers",
        json={
            "hostname": "web-server-01",
            "ip_address": "192.168.1.100",
            "os_type": "Linux",
            "environment": "production",
            "customer_id": customer_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "web-server-01"
    assert data["customer_id"] == customer_id


@pytest.mark.asyncio
async def test_search_endpoint(client: AsyncClient):
    customer_response = await client.post(
        "/api/v1/customers",
        json={"name": "Search Test Customer", "code": "SearchTest"}
    )
    customer_id = customer_response.json()["id"]
    
    response = await client.post(
        "/api/v1/search",
        json={
            "query": "test",
            "customer_id": customer_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_chat_endpoint(client: AsyncClient):
    customer_response = await client.post(
        "/api/v1/customers",
        json={"name": "Chat Test Customer", "code": "ChatTest"}
    )
    customer_id = customer_response.json()["id"]
    
    response = await client.post(
        "/api/v1/chat",
        json={
            "query": "How do I restart the database?",
            "customer_id": customer_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "evidence" in data
