# import asyncio
# import sys
# import os
# from dotenv import load_dotenv, find_dotenv
# from contextlib import AsyncExitStack

# from mcp_client import MCPClient
# from core.agent_service import AgentService

# from core.cli_chat import CliChat
# from core.cli import CliApp

# load_dotenv(find_dotenv(filename=".env"))

# # Agent Config
# llm_model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
# llm_api_key = os.getenv("LLM_MODEL_API_KEY", "AIzaSyD52ML7yU3DBM5S2QNfhSj5sE5dt-oyGCI")
# llm_base_url = os.getenv("LLM_CHAT_COMPLETION_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

# assert llm_model, "Error: LLM_MODEL cannot be empty. Update .env"
# assert llm_api_key, (
#     "Error: LLM_API_KEY cannot be empty. Update .env"
# )
# assert llm_base_url, (
#     "Error: LLM_CHAT_COMPLETION_URL cannot be empty. Update .env"
# )


# async def main():
#     server_scripts = sys.argv[1:]
#     clients = {}

#     # command, args = ("uv", ["run", "mcp_server.py"])
#     server_url = "http://localhost:8000/mcp/"

#     async with AsyncExitStack() as stack:
#         doc_client = await stack.enter_async_context(
#             MCPClient(server_url=server_url)
#         )
#         clients["doc_client"] = doc_client

#         for i, server_script in enumerate(server_scripts):
#             client_id = f"client_{i}_{server_script}"
#             client = await stack.enter_async_context(
#                 MCPClient(command="uv", args=["run", server_script])
#             )
#             clients[client_id] = client

#         agent_service = AgentService(
#             model=llm_model,
#             api_key=llm_api_key,
#             base_url=llm_base_url,
#             clients=clients
#         )

#         chat = CliChat(
#             doc_client=doc_client,
#             clients=clients,
#             agent_serve=agent_service,
#         )

#         cli = CliApp(chat)
#         await cli.initialize()
#         await cli.run()


# if __name__ == "__main__":
#     if sys.platform == "win32":
#         asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
#     asyncio.run(main())


from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP(name="MCP", stateless_http=True)


@mcp.prompt(name="hello_prompt", description="This is for greeeting", title="Hello")
async def hello_prompt() -> list[base.UserMessage]:
    user_message = f"Hello"
    return [base.UserMessage(content=user_message)]


mcp_app = mcp.streamable_http_app()
