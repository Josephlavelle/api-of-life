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


class Item(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": app.version}


@app.get("/items", response_model=list[Item])
def list_items(search: Optional[str] = None, limit: Optional[int] = None, sort: Optional[str] = None):
    """List all items in the store. Optionally filter by name or description, sort by creation date, and limit results."""
    items = list(items_db.values())
    if search:
        search_lower = search.lower()
        items = [item for item in items if search_lower in item["name"].lower() or
                 (item["description"] and search_lower in item["description"].lower())]
    if sort in ["asc", "desc"]:
        items = sorted(items, key=lambda x: x["created_at"], reverse=(sort == "desc"))
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
        "created_at": now,
        "updated_at": now
    }
    items_db[item_id] = new_item
    return new_item


@app.get("/items/count")
def get_items_count():
    """Get the total number of items in the store."""
    return {"count": len(items_db)}


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
    items_db[item_id]["updated_at"] = datetime.now().isoformat()
    return items_db[item_id]


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str):
    """Delete an item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
