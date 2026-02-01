"""Tests for the API of Life."""

import pytest
from fastapi.testclient import TestClient
from main import app, items_db


@pytest.fixture(autouse=True)
def clear_db():
    """Clear the database before each test."""
    items_db.clear()
    yield
    items_db.clear()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_items_empty(client):
    """Test listing items when store is empty."""
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == []


def test_create_item(client):
    """Test creating a new item."""
    response = client.post("/items", json={"name": "Test Item", "description": "A test"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "A test"
    assert "id" in data


def test_create_item_minimal(client):
    """Test creating an item with only required fields."""
    response = client.post("/items", json={"name": "Minimal Item"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Item"
    assert data["description"] is None


def test_get_item(client):
    """Test getting a single item."""
    # First create an item
    create_response = client.post("/items", json={"name": "Get Test"})
    item_id = create_response.json()["id"]

    # Then retrieve it
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "Get Test"


def test_get_item_not_found(client):
    """Test getting a non-existent item."""
    response = client.get("/items/nonexistent-id")
    assert response.status_code == 404


def test_list_items_with_data(client):
    """Test listing items after creating some."""
    client.post("/items", json={"name": "Item 1"})
    client.post("/items", json={"name": "Item 2"})

    response = client.get("/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2


def test_delete_item(client):
    """Test deleting an item."""
    create_response = client.post("/items", json={"name": "Delete Me"})
    item_id = create_response.json()["id"]

    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 204

    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 404


def test_delete_item_not_found(client):
    """Test deleting a non-existent item."""
    response = client.delete("/items/nonexistent-id")
    assert response.status_code == 404


def test_items_count_empty(client):
    """Test item count when store is empty."""
    response = client.get("/items/count")
    assert response.status_code == 200
    assert response.json() == {"count": 0}


def test_items_count_with_data(client):
    """Test item count after creating items."""
    client.post("/items", json={"name": "Item 1"})
    client.post("/items", json={"name": "Item 2"})
    client.post("/items", json={"name": "Item 3"})

    response = client.get("/items/count")
    assert response.status_code == 200
    assert response.json() == {"count": 3}
