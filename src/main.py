"""
API of Life - A self-evolving FastAPI application.

This API evolves daily through Claude Code suggestions and implementations.
See evolution/history.md for the complete evolution log.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4

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


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": app.version}


@app.get("/items", response_model=list[Item])
def list_items():
    """List all items in the store."""
    return list(items_db.values())


@app.post("/items", response_model=Item, status_code=201)
def create_item(item: ItemCreate):
    """Create a new item."""
    item_id = str(uuid4())
    new_item = {"id": item_id, "name": item.name, "description": item.description}
    items_db[item_id] = new_item
    return new_item


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str):
    """Get a single item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]
