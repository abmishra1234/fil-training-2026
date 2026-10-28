"""
mcp_server.py - STRETCH GOAL: expose the same Action as an MCP tool.

The model now discovers the tool's JSON Schema through MCP instead of reading
SKILL.md, and errors come back as tool results it can retry on.

    pip install mcp
    python scripts/mcp_server.py          # stdio transport, for any MCP client
"""
try:                                   # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:                    # MCP Python SDK 1.x
    from mcp.server.fastmcp import FastMCP as Server

from totals import compute, validate

mcp = Server("fil-invoice-tools")


@mcp.tool()
def compute_invoice_totals(lines: list[dict], gst_rate: float, stated_total: float | None = None) -> dict:
    """Exact subtotal, GST and total for one vendor invoice.

    lines: [{"description": str, "qty": number > 0, "price": number >= 0}, ...]
    gst_rate: one of 0, 5, 12, 18, 28 (percent)
    stated_total: grand total printed on the invoice, if you want a MISMATCH check
    On bad input returns {"error", "field", "fix", "retryable"}: follow the fix and call again.
    """
    data = {"lines": lines, "gst_rate": int(gst_rate) if float(gst_rate).is_integer() else gst_rate}
    if stated_total is not None:
        data["stated_total"] = stated_total
    problem = validate(data)
    if problem:
        problem.setdefault("retryable", True)
        return problem
    return compute(data)


if __name__ == "__main__":
    mcp.run()
