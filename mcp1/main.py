from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="hello_mcp",stateless_http = True)

@mcp.tool()
def get_weather(city:str)->str:
    return f"the weather in {city} is sunny"

mcp_app = mcp.streamable_http_app()