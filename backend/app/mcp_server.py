from mcp.server.fastmcp import FastMCP

from app.security.tool_dispatcher import dispatch_tool


mcp = FastMCP("JibuTax")


@mcp.tool()
async def verify_pin(pin: str) -> dict:
    return await dispatch_tool(
        tool_name="verify_pin",
        raw_arguments={
            "pin": pin,
        },
    )

@mcp.tool()
async def submit_invoice(
    seller_pin: str,
    buyer_pin: str,
    items: list[dict],
    send_sms: bool,
    buyer_phone: str | None,
    confirmation_token: str,
) -> dict:
    return await dispatch_tool(
        tool_name="submit_invoice",
        raw_arguments={
            "seller_pin": seller_pin,
            "buyer_pin": buyer_pin,
            "items": items,
            "send_sms": send_sms,
            "buyer_phone": buyer_phone,
            "confirmation_token": confirmation_token,
        },
    )