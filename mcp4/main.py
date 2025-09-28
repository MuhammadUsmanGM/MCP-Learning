from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

mcp = FastMCP(name="MCP_APP",stateless_http=True)

docs = {
    "intro": "This is a simple step of a stateless MCP server",
    "readme": "This server supports basic MCP operations",
    "guide": "Refer to the documentation for more details",
}

@mcp.resource("docs://documents",
                description="collection of docs",
                mime_type="application/json")
def list_docs():
    return list(docs.keys())

print("LIST DOCS",list_docs())

mcp_app: Starlette = mcp.streamable_http_app()