"""Meta WhatsApp Cloud API webhook: verify callback URL and log inbound opt-in messages."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhook")
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed.")


@router.post("/webhook")
async def receive_whatsapp_webhook(request: Request):
    payload = await request.json()
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for message in value.get("messages") or []:
                logger.info(
                    "whatsapp_inbound from=%s type=%s",
                    message.get("from"),
                    message.get("type"),
                )
    return {"ok": True}
