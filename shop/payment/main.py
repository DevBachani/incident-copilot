"""payment — simulated payment processing."""

from __future__ import annotations

from fastapi import Body

from shop.common.app import create_app
from shop.common.faults import state

app = create_app("payment")


@app.post("/pay")
def pay(order: dict = Body(default={})) -> dict:
    if state.bad_data:
        return {"status": "???"}  # malformed: missing txn, unknown status
    return {"status": "paid", "txn": "tx-123", "amount": order.get("amount", 0)}
