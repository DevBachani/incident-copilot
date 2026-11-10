"""frontend — entry point; fans out to catalog, cart, checkout."""

from __future__ import annotations

import os

import httpx

from shop.common.app import create_app

app = create_app("frontend")

CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog:8000")
CART_URL = os.getenv("CART_URL", "http://cart:8000")
CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://checkout:8000")
TIMEOUT = float(os.getenv("DEP_TIMEOUT_S", "5"))


@app.get("/")
async def home() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        products = (await client.get(f"{CATALOG_URL}/products")).json()
    return {"ok": True, "product_count": len(products) if isinstance(products, list) else 0}


@app.post("/buy")
async def buy() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        await client.post(f"{CART_URL}/cart/demo", json={"id": 1, "qty": 1})
        result = (await client.post(f"{CHECKOUT_URL}/checkout", json={"cart_id": "demo"})).json()
    return result
