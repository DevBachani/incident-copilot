"""cart — in-memory cart state (a real Redis backs this in the Helm chart later)."""

from __future__ import annotations

from fastapi import Body

from shop.common.app import create_app

app = create_app("cart")

_carts: dict[str, list[dict]] = {}


@app.get("/cart/{cart_id}")
def get_cart(cart_id: str) -> dict:
    return {"id": cart_id, "items": _carts.get(cart_id, [])}


@app.post("/cart/{cart_id}")
def add_item(cart_id: str, item: dict = Body(default={})) -> dict:
    _carts.setdefault(cart_id, []).append(item)
    return {"id": cart_id, "items": _carts[cart_id]}
