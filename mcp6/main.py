from mcp.server.fastmcp import FastMCP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="Agent_SDK",
            stateless_http=True)

@mcp.tool(name="greeting",
        description="Return a personalized greeting from the mcp server")

def greet(name:str="World")-> str:
    logger.info(f"Tool 'greet' called with name {name}")
    response_message = f"Hello {name},from shared MCP server"
    return response_message


@mcp.tool(name="get_mood",
        description="Return a user mood from the mcp server")
@mcp.prompt(name="general_chat")
def general_chat(user_name:str)->str:
    return f"You are a general list agent that help {user_name} with everything."
def greet(name:str="World")-> str:
    logger.info(f"Tool 'mood' called with name {name}")
    response_message = f"User {name} is happy"
    return response_message


mcp_app = mcp.streamable_http_app()