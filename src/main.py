"""
API of Life - A self-evolving FastAPI application.

This API evolves daily through Claude Code suggestions and implementations.
See evolution/history.md for the complete evolution log.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from datetime import datetime

app = FastAPI(
    title="API of Life",
    description="A self-evolving API that grows new features daily",
    version="0.1.0"
)

# In-memory store
items_db: dict[str, dict] = {}


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    active: Optional[bool] = True
    priority: Optional[int] = 0


class ItemPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    active: Optional[bool] = None
    priority: Optional[int] = None


class Item(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    active: bool
    priority: int
    created_at: str
    updated_at: str


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": app.version}


@app.get("/items", response_model=list[Item])
def list_items(search: Optional[str] = None, limit: Optional[int] = None, sort: Optional[str] = None, sort_by: Optional[str] = None, created_after: Optional[str] = None, created_before: Optional[str] = None, tags: Optional[str] = None, offset: Optional[int] = None, active: Optional[bool] = None, priority: Optional[int] = None, min_priority: Optional[int] = None, max_priority: Optional[int] = None):
    """List all items in the store. Optionally filter by name or description, sort by name or creation date, paginate with offset and limit results."""
    items = list(items_db.values())
    if search:
        search_lower = search.lower()
        items = [item for item in items if search_lower in item["name"].lower() or
                 (item["description"] and search_lower in item["description"].lower()) or
                 (item.get("notes") and search_lower in item["notes"].lower())]
    if created_after:
        items = [item for item in items if item["created_at"] >= created_after]
    if created_before:
        items = [item for item in items if item["created_at"] <= created_before]
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        items = [item for item in items if any(tag in item.get("tags", []) for tag in tag_list)]
    if active is not None:
        items = [item for item in items if item.get("active") == active]
    if priority is not None:
        items = [item for item in items if item.get("priority") == priority]
    if min_priority is not None:
        items = [i for i in items if i["priority"] >= min_priority]
    if max_priority is not None:
        items = [i for i in items if i["priority"] <= max_priority]
    if sort in ["asc", "desc"]:
        sort_key = sort_by if sort_by in ["name", "created_at", "updated_at", "priority"] else "created_at"
        items = sorted(items, key=lambda x: x[sort_key], reverse=(sort == "desc"))
    if offset is not None:
        items = items[offset:]
    if limit is not None:
        items = items[:limit]
    return items


@app.post("/items", response_model=Item, status_code=201)
def create_item(item: ItemCreate):
    """Create a new item."""
    item_id = str(uuid4())
    now = datetime.now().isoformat()
    new_item = {
        "id": item_id,
        "name": item.name,
        "description": item.description,
        "notes": item.notes,
        "tags": item.tags,
        "active": item.active if item.active is not None else True,
        "priority": item.priority if item.priority is not None else 0,
        "created_at": now,
        "updated_at": now
    }
    items_db[item_id] = new_item
    return new_item


@app.get("/items/count")
def get_items_count():
    """Get the total number of items in the store."""
    return {"count": len(items_db)}


@app.delete("/items")
def delete_all_items():
    """Delete all items from the store."""
    count = len(items_db)
    items_db.clear()
    return {"deleted": count}


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str):
    """Get a single item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: str, item: ItemCreate):
    """Update an item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id]["name"] = item.name
    items_db[item_id]["description"] = item.description
    items_db[item_id]["notes"] = item.notes
    items_db[item_id]["tags"] = item.tags
    items_db[item_id]["active"] = item.active if item.active is not None else True
    items_db[item_id]["priority"] = item.priority if item.priority is not None else 0
    items_db[item_id]["updated_at"] = datetime.now().isoformat()
    return items_db[item_id]


@app.patch("/items/{item_id}", response_model=Item)
def patch_item(item_id: str, item: ItemPatch):
    """Partially update an item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    updates = item.model_dump(exclude_none=True)
    if updates:
        items_db[item_id].update(updates)
        items_db[item_id]["updated_at"] = datetime.now().isoformat()
    return items_db[item_id]


@app.post("/items/{item_id}/duplicate", response_model=Item, status_code=201)
def duplicate_item(item_id: str):
    """Duplicate an existing item with a new ID and fresh timestamps."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    source = items_db[item_id]
    now = datetime.now().isoformat()
    new_item = {**source, "id": str(uuid4()), "created_at": now, "updated_at": now}
    items_db[new_item["id"]] = new_item
    return new_item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str):
    """Delete an item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
