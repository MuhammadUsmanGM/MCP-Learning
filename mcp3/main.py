from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

mcp = FastMCP(name="MCP_APP", stateless_http=True)

docs = {}  # Add this to avoid errors

@mcp.tool()
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny"

@mcp.tool()
def get_greeting(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool()
async def read_doc(doc_id: str) -> str:
    return docs.get(doc_id, "Document not found")

@mcp.tool()
async def edit_doc(doc_id: str, content: str) -> str:
    docs[doc_id] = content
    return "Document edited successfully"

mcp_app: Starlette = mcp.streamable_http_app()

# ✅ Start the MCP server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        mcp_app,
        host="0.0.0.0",
        port=8000
    )
