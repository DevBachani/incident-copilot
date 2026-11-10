"""catalog — product list from an in-memory store."""

from __future__ import annotations

from shop.common.app import create_app
from shop.common.faults import state

app = create_app("catalog")

_PRODUCTS = [{"id": i, "name": f"item-{i}", "price": i * 10} for i in range(1, 11)]


@app.get("/products")
def products() -> object:
    if state.bad_data:
        return {"unexpected": "not-a-list"}  # malformed: breaks callers expecting a list
    return _PRODUCTS
