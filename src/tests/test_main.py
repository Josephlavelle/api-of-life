"""Tests for the API of Life."""

import pytest
from datetime import datetime
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


def test_search_items(client):
    """Test searching items by name."""
    client.post("/items", json={"name": "Apple Pie"})
    client.post("/items", json={"name": "Banana Bread"})
    client.post("/items", json={"name": "Apple Juice"})

    response = client.get("/items?search=apple")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all("apple" in item["name"].lower() for item in items)


def test_search_items_case_insensitive(client):
    """Test that search is case-insensitive."""
    client.post("/items", json={"name": "Test Item"})
    client.post("/items", json={"name": "Another Thing"})

    response = client.get("/items?search=TEST")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Test Item"


def test_search_items_no_match(client):
    """Test searching with no matches."""
    client.post("/items", json={"name": "Foo"})
    client.post("/items", json={"name": "Bar"})

    response = client.get("/items?search=baz")
    assert response.status_code == 200
    assert response.json() == []


def test_list_items_with_limit(client):
    """Test limiting the number of items returned."""
    client.post("/items", json={"name": "Item 1"})
    client.post("/items", json={"name": "Item 2"})
    client.post("/items", json={"name": "Item 3"})
    client.post("/items", json={"name": "Item 4"})

    response = client.get("/items?limit=2")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2


def test_list_items_limit_with_search(client):
    """Test limit works with search parameter."""
    client.post("/items", json={"name": "Apple Pie"})
    client.post("/items", json={"name": "Apple Juice"})
    client.post("/items", json={"name": "Apple Tart"})

    response = client.get("/items?search=apple&limit=2")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all("apple" in item["name"].lower() for item in items)


def test_item_has_created_timestamp(client):
    """Test that created items have a created_at timestamp."""
    response = client.post("/items", json={"name": "Timestamped Item"})
    assert response.status_code == 201
    data = response.json()
    assert "created_at" in data

    # Verify it's a valid ISO format timestamp
    created_at = datetime.fromisoformat(data["created_at"])
    assert isinstance(created_at, datetime)


def test_sort_items_ascending(client):
    """Test sorting items by creation date in ascending order."""
    client.post("/items", json={"name": "First"})
    client.post("/items", json={"name": "Second"})
    client.post("/items", json={"name": "Third"})

    response = client.get("/items?sort=asc")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert items[0]["name"] == "First"
    assert items[2]["name"] == "Third"


def test_sort_items_descending(client):
    """Test sorting items by creation date in descending order."""
    client.post("/items", json={"name": "First"})
    client.post("/items", json={"name": "Second"})
    client.post("/items", json={"name": "Third"})

    response = client.get("/items?sort=desc")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert items[0]["name"] == "Third"
    assert items[2]["name"] == "First"


def test_sort_with_limit(client):
    """Test sorting works with limit parameter."""
    client.post("/items", json={"name": "First"})
    client.post("/items", json={"name": "Second"})
    client.post("/items", json={"name": "Third"})

    response = client.get("/items?sort=desc&limit=2")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["name"] == "Third"
    assert items[1]["name"] == "Second"


def test_update_item(client):
    """Test updating an item."""
    create_response = client.post("/items", json={"name": "Old Name", "description": "Old Desc"})
    item_id = create_response.json()["id"]

    response = client.put(f"/items/{item_id}", json={"name": "New Name", "description": "New Desc"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "New Desc"
    assert data["id"] == item_id


def test_update_item_not_found(client):
    """Test updating a non-existent item."""
    response = client.put("/items/nonexistent-id", json={"name": "New Name"})
    assert response.status_code == 404


def test_update_item_partial(client):
    """Test updating an item with partial fields."""
    create_response = client.post("/items", json={"name": "Original", "description": "Desc"})
    item_id = create_response.json()["id"]

    response = client.put(f"/items/{item_id}", json={"name": "Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] is None
