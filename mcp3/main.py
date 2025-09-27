from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
mcp = FastMCP(name="MCP_APP",stateless_http=True)

@mcp.tool()
def get_weather(city:str)->str:
    return f"the weather in {city} is sunny"
@mcp.tool()
def get_greeting(name: str) -> str:
    return f"Hello, {name}!"
# TODO: Write a tool to read a doc
@mcp.tool()
async def read_doc(doc_id:str)->str:
    return docs[doc_id]
# TODO: Write a tool to edit a doc
@mcp.tool()
async def edit_doc(doc_id:str,content:str)->str:
    docs[doc_id] = content
    return "Document edited successfully"

mcp_app: Starlette = mcp.streamable_http_app()