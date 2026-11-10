"""checkout — orchestrates an order across cart and payment."""

from __future__ import annotations

import os

import httpx
from fastapi import Body

from shop.common.app import create_app

app = create_app("checkout")

CART_URL = os.getenv("CART_URL", "http://cart:8000")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://payment:8000")
TIMEOUT = float(os.getenv("DEP_TIMEOUT_S", "5"))


@app.post("/checkout")
async def checkout(order: dict = Body(default={})) -> dict:
    cart_id = order.get("cart_id", "demo")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        cart = (await client.get(f"{CART_URL}/cart/{cart_id}")).json()
        payment = (await client.post(f"{PAYMENT_URL}/pay", json={"amount": 100})).json()
    return {"status": "ok", "cart": cart, "payment": payment}
