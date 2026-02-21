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


def test_search_items_by_description(client):
    """Test searching items by description."""
    client.post("/items", json={"name": "Apple", "description": "A delicious red fruit"})
    client.post("/items", json={"name": "Carrot", "description": "An orange vegetable"})
    client.post("/items", json={"name": "Banana", "description": "A yellow fruit"})

    response = client.get("/items?search=fruit")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all("fruit" in item["description"].lower() for item in items)


def test_search_items_by_name_or_description(client):
    """Test searching items matches both name and description."""
    client.post("/items", json={"name": "Orange Juice", "description": "Made from oranges"})
    client.post("/items", json={"name": "Apple", "description": "Contains orange vitamin C"})
    client.post("/items", json={"name": "Grape", "description": "Purple fruit"})

    response = client.get("/items?search=orange")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Orange Juice" in names
    assert "Apple" in names


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


def test_item_has_updated_at_timestamp(client):
    """Test that created items have an updated_at timestamp."""
    response = client.post("/items", json={"name": "Test Item"})
    assert response.status_code == 201
    data = response.json()
    assert "updated_at" in data
    assert data["created_at"] == data["updated_at"]  # Should be same on creation


def test_update_item_changes_updated_at(client):
    """Test that updating an item changes the updated_at timestamp."""
    import time

    create_response = client.post("/items", json={"name": "Original"})
    item_id = create_response.json()["id"]
    original_updated_at = create_response.json()["updated_at"]

    time.sleep(0.01)  # Small delay to ensure different timestamp

    update_response = client.put(f"/items/{item_id}", json={"name": "Updated"})
    data = update_response.json()
    assert data["updated_at"] != original_updated_at
    assert data["created_at"] != data["updated_at"]  # Should be different after update


def test_delete_all_items_empty(client):
    """Test bulk delete on empty store."""
    response = client.delete("/items")
    assert response.status_code == 200
    assert response.json() == {"deleted": 0}


def test_delete_all_items_with_data(client):
    """Test bulk delete removes all items."""
    client.post("/items", json={"name": "Item 1"})
    client.post("/items", json={"name": "Item 2"})
    client.post("/items", json={"name": "Item 3"})

    response = client.delete("/items")
    assert response.status_code == 200
    assert response.json() == {"deleted": 3}

    list_response = client.get("/items")
    assert list_response.json() == []


def test_filter_by_created_after(client):
    """Test filtering items by created_after date."""
    import time

    response1 = client.post("/items", json={"name": "Item 1"})
    item1_created = response1.json()["created_at"]

    time.sleep(0.01)

    response2 = client.post("/items", json={"name": "Item 2"})
    item2_created = response2.json()["created_at"]

    time.sleep(0.01)

    client.post("/items", json={"name": "Item 3"})

    # Filter items created after item1
    response = client.get(f"/items?created_after={item2_created}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(item["created_at"] >= item2_created for item in items)


def test_filter_by_created_before(client):
    """Test filtering items by created_before date."""
    import time

    client.post("/items", json={"name": "Item 1"})

    time.sleep(0.01)

    response2 = client.post("/items", json={"name": "Item 2"})
    item2_created = response2.json()["created_at"]

    time.sleep(0.01)

    client.post("/items", json={"name": "Item 3"})

    # Filter items created before item3
    response = client.get(f"/items?created_before={item2_created}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(item["created_at"] <= item2_created for item in items)


def test_filter_by_date_range(client):
    """Test filtering items by date range (created_after and created_before)."""
    import time

    client.post("/items", json={"name": "Item 1"})

    time.sleep(0.01)

    response2 = client.post("/items", json={"name": "Item 2"})
    item2_created = response2.json()["created_at"]

    time.sleep(0.01)

    response3 = client.post("/items", json={"name": "Item 3"})
    item3_created = response3.json()["created_at"]

    time.sleep(0.01)

    client.post("/items", json={"name": "Item 4"})

    # Filter items in the middle range
    response = client.get(f"/items?created_after={item2_created}&created_before={item3_created}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 2" in names
    assert "Item 3" in names


def test_create_item_with_tags(client):
    """Test creating an item with tags."""
    response = client.post("/items", json={"name": "Tagged Item", "tags": ["work", "urgent"]})
    assert response.status_code == 201
    data = response.json()
    assert data["tags"] == ["work", "urgent"]


def test_filter_items_by_tag(client):
    """Test filtering items by a specific tag."""
    client.post("/items", json={"name": "Item 1", "tags": ["work", "urgent"]})
    client.post("/items", json={"name": "Item 2", "tags": ["personal"]})
    client.post("/items", json={"name": "Item 3", "tags": ["work"]})

    response = client.get("/items?tags=work")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 3" in names


def test_update_item_with_tags(client):
    """Test updating an item's tags."""
    create_response = client.post("/items", json={"name": "Item", "tags": ["old"]})
    item_id = create_response.json()["id"]

    response = client.put(f"/items/{item_id}", json={"name": "Item", "tags": ["new", "updated"]})
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["new", "updated"]


def test_list_items_with_offset(client):
    """Test using offset to skip items."""
    client.post("/items", json={"name": "Item 1"})
    client.post("/items", json={"name": "Item 2"})
    client.post("/items", json={"name": "Item 3"})
    client.post("/items", json={"name": "Item 4"})

    response = client.get("/items?offset=2")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2


def test_list_items_with_offset_and_limit(client):
    """Test offset and limit work together for pagination."""
    client.post("/items", json={"name": "Item 1"})
    client.post("/items", json={"name": "Item 2"})
    client.post("/items", json={"name": "Item 3"})
    client.post("/items", json={"name": "Item 4"})
    client.post("/items", json={"name": "Item 5"})

    response = client.get("/items?offset=1&limit=2")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2


def test_sort_items_by_name_ascending(client):
    """Test sorting items by name in ascending order."""
    client.post("/items", json={"name": "Zebra"})
    client.post("/items", json={"name": "Apple"})
    client.post("/items", json={"name": "Mango"})

    response = client.get("/items?sort=asc&sort_by=name")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert items[0]["name"] == "Apple"
    assert items[1]["name"] == "Mango"
    assert items[2]["name"] == "Zebra"


def test_sort_items_by_name_descending(client):
    """Test sorting items by name in descending order."""
    client.post("/items", json={"name": "Zebra"})
    client.post("/items", json={"name": "Apple"})
    client.post("/items", json={"name": "Mango"})

    response = client.get("/items?sort=desc&sort_by=name")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert items[0]["name"] == "Zebra"
    assert items[1]["name"] == "Mango"
    assert items[2]["name"] == "Apple"


def test_create_item_defaults_to_active(client):
    """Test that items default to active=True."""
    response = client.post("/items", json={"name": "Active Item"})
    assert response.status_code == 201
    data = response.json()
    assert data["active"] is True


def test_create_inactive_item(client):
    """Test creating an item with active=False."""
    response = client.post("/items", json={"name": "Inactive Item", "active": False})
    assert response.status_code == 201
    data = response.json()
    assert data["active"] is False


def test_filter_active_items(client):
    """Test filtering items by active status."""
    client.post("/items", json={"name": "Active Item", "active": True})
    client.post("/items", json={"name": "Inactive Item", "active": False})
    client.post("/items", json={"name": "Also Active"})

    response = client.get("/items?active=true")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(item["active"] is True for item in items)

    response = client.get("/items?active=false")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Inactive Item"


def test_create_item_with_priority(client):
    """Test creating an item with priority."""
    response = client.post("/items", json={"name": "High Priority", "priority": 5})
    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == 5


def test_filter_items_by_priority(client):
    """Test filtering items by priority level."""
    client.post("/items", json={"name": "Low", "priority": 1})
    client.post("/items", json={"name": "High", "priority": 5})
    client.post("/items", json={"name": "Also High", "priority": 5})

    response = client.get("/items?priority=5")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(item["priority"] == 5 for item in items)


def test_sort_items_by_priority_ascending(client):
    """Test sorting items by priority in ascending order."""
    client.post("/items", json={"name": "High", "priority": 5})
    client.post("/items", json={"name": "Low", "priority": 1})
    client.post("/items", json={"name": "Medium", "priority": 3})

    response = client.get("/items?sort=asc&sort_by=priority")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert items[0]["priority"] == 1
    assert items[1]["priority"] == 3
    assert items[2]["priority"] == 5


def test_sort_items_by_priority_descending(client):
    """Test sorting items by priority in descending order."""
    client.post("/items", json={"name": "High", "priority": 5})
    client.post("/items", json={"name": "Low", "priority": 1})
    client.post("/items", json={"name": "Medium", "priority": 3})

    response = client.get("/items?sort=desc&sort_by=priority")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert items[0]["priority"] == 5
    assert items[1]["priority"] == 3
    assert items[2]["priority"] == 1


def test_filter_items_by_min_priority(client):
    """Test filtering items by minimum priority."""
    client.post("/items", json={"name": "Low", "priority": 1})
    client.post("/items", json={"name": "Medium", "priority": 3})
    client.post("/items", json={"name": "High", "priority": 5})

    response = client.get("/items?min_priority=3")
    assert response.status_code == 200
    items = response.json()
    assert all(item["priority"] >= 3 for item in items)
    assert len(items) == 2


def test_filter_items_by_max_priority(client):
    """Test filtering items by maximum priority."""
    client.post("/items", json={"name": "Low", "priority": 1})
    client.post("/items", json={"name": "Medium", "priority": 3})
    client.post("/items", json={"name": "High", "priority": 5})

    response = client.get("/items?max_priority=3")
    assert response.status_code == 200
    items = response.json()
    assert all(item["priority"] <= 3 for item in items)
    assert len(items) == 2


def test_filter_items_by_priority_range(client):
    """Test filtering items by priority range (min and max)."""
    client.post("/items", json={"name": "Low", "priority": 1})
    client.post("/items", json={"name": "Medium", "priority": 3})
    client.post("/items", json={"name": "High", "priority": 5})

    response = client.get("/items?min_priority=2&max_priority=4")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["priority"] == 3


def test_create_item_with_notes(client):
    """Test creating an item with notes."""
    response = client.post("/items", json={"name": "Item", "notes": "Some additional context"})
    assert response.status_code == 201
    data = response.json()
    assert data["notes"] == "Some additional context"


def test_update_item_with_notes(client):
    """Test updating an item's notes."""
    create_response = client.post("/items", json={"name": "Item", "notes": "Old notes"})
    item_id = create_response.json()["id"]

    response = client.put(f"/items/{item_id}", json={"name": "Item", "notes": "Updated notes"})
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Updated notes"


def test_search_items_by_notes(client):
    """Test searching items by notes field."""
    client.post("/items", json={"name": "Item 1", "notes": "Meeting scheduled for tomorrow"})
    client.post("/items", json={"name": "Item 2", "notes": "Follow up with client"})
    client.post("/items", json={"name": "Item 3", "notes": "Schedule next meeting"})

    response = client.get("/items?search=meeting")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 3" in names


def test_search_items_by_name_description_or_notes(client):
    """Test searching items matches name, description, or notes."""
    client.post("/items", json={"name": "Project Alpha", "description": "Initial setup", "notes": "Check budget"})
    client.post("/items", json={"name": "Budget Review", "description": "Monthly financial check", "notes": "Due next week"})
    client.post("/items", json={"name": "Team Meeting", "description": "Weekly sync", "notes": "Discuss budget allocation"})

    response = client.get("/items?search=budget")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3


def test_filter_items_by_multiple_tags(client):
    """Test filtering items by multiple tags (comma-separated)."""
    client.post("/items", json={"name": "Item 1", "tags": ["work", "urgent"]})
    client.post("/items", json={"name": "Item 2", "tags": ["personal", "urgent"]})
    client.post("/items", json={"name": "Item 3", "tags": ["work"]})
    client.post("/items", json={"name": "Item 4", "tags": ["personal"]})

    response = client.get("/items?tags=work,urgent")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 2" in names
    assert "Item 3" in names


def test_sort_by_updated_at(client):
    """Test sorting items by updated_at returns recently-updated item first."""
    r1 = client.post("/items", json={"name": "Item A"})
    r2 = client.post("/items", json={"name": "Item B"})
    item_a_id = r1.json()["id"]

    # Update Item A so its updated_at is more recent than Item B's
    client.put(f"/items/{item_a_id}", json={"name": "Item A Updated"})

    response = client.get("/items?sort=desc&sort_by=updated_at")
    assert response.status_code == 200
    items = response.json()
    assert items[0]["id"] == item_a_id


def test_patch_item_single_field(client):
    """Test patching a single field leaves other fields unchanged."""
    create_response = client.post("/items", json={"name": "Original", "description": "Desc", "priority": 3})
    item_id = create_response.json()["id"]

    response = client.patch(f"/items/{item_id}", json={"name": "Patched"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Patched"
    assert data["description"] == "Desc"
    assert data["priority"] == 3


def test_patch_item_multiple_fields(client):
    """Test patching multiple fields at once."""
    create_response = client.post("/items", json={"name": "Original", "priority": 1, "active": True})
    item_id = create_response.json()["id"]

    response = client.patch(f"/items/{item_id}", json={"priority": 5, "active": False})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Original"
    assert data["priority"] == 5
    assert data["active"] is False


def test_patch_item_not_found(client):
    """Test patching a non-existent item returns 404."""
    response = client.patch("/items/nonexistent-id", json={"name": "X"})
    assert response.status_code == 404


def test_duplicate_item(client):
    """Test duplicating an item creates a copy with a new ID."""
    create_response = client.post("/items", json={"name": "Original", "priority": 3, "tags": ["work"]})
    item_id = create_response.json()["id"]

    response = client.post(f"/items/{item_id}/duplicate")
    assert response.status_code == 201
    data = response.json()
    assert data["id"] != item_id
    assert data["name"] == "Original"
    assert data["priority"] == 3
    assert data["tags"] == ["work"]


def test_duplicate_item_not_found(client):
    """Test duplicating a non-existent item returns 404."""
    response = client.post("/items/nonexistent-id/duplicate")
    assert response.status_code == 404


def test_duplicate_item_stored_independently(client):
    """Test that the duplicate is stored and independent from the original."""
    create_response = client.post("/items", json={"name": "Source"})
    item_id = create_response.json()["id"]

    dup_response = client.post(f"/items/{item_id}/duplicate")
    dup_id = dup_response.json()["id"]

    # Both items exist
    assert client.get(f"/items/{item_id}").status_code == 200
    assert client.get(f"/items/{dup_id}").status_code == 200

    # Total count is 2
    assert client.get("/items/count").json()["count"] == 2


def test_filter_items_by_multiple_tags_with_spaces(client):
    """Test filtering items by multiple tags with spaces in query."""
    client.post("/items", json={"name": "Item 1", "tags": ["work", "important"]})
    client.post("/items", json={"name": "Item 2", "tags": ["personal"]})
    client.post("/items", json={"name": "Item 3", "tags": ["work"]})

    response = client.get("/items?tags=work, important")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 3" in names
