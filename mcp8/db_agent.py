from agents import (Agent,
                    Runner,
                    AsyncOpenAI,
                    OpenAIChatCompletionsModel,
                    set_default_openai_api,
                    set_default_openai_client,
                    set_tracing_disabled,)
from my_secrets import Secrets
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams, create_static_tool_filter, ToolFilterContext
import asyncio

secrets = Secrets()

external_client = AsyncOpenAI(
    api_key=secrets.gemini_api_key,
    base_url = secrets.gemini_base_url)
set_default_openai_client(external_client)
set_tracing_disabled(True)
set_default_openai_api("chat_completions")
model = OpenAIChatCompletionsModel(
    model=secrets.gemini_api_model,
    openai_client=external_client
)
async def main():
    params_config = MCPServerStreamableHttpParams(url="http://127.0.0.1:8000/mcp")
    async with MCPServerStreamableHttp(params=params_config, name="Assistant_Server", cache_tools_list = True) as mcp_server:
        mcp_server.invalidate_tools_cache()
        await mcp_server.connect()

        greet = await mcp_server.get_prompt("instructions")

        agent = Agent(
            name="Assistant",
            instructions=greet.messages[0].content.text,
            model=model,
            mcp_servers=[mcp_server]
        )

        # Test enhanced natural language queries
        result = await Runner.run(
            agent,
            "What's the id of the member named Alice?")
        print("=== MEMBER ID LOOKUP ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "What's the details for the member Bob?")
        print("=== MEMBER DETAILS ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Who is the author of book Clean Code?")
        print("=== BOOK AUTHOR LOOKUP ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Count all books in the collection")
        print("=== COUNT BOOKS ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "How many members do we have?")
        print("=== COUNT MEMBERS ===")
        print(result.final_output)

        result = await Runner.run(
            agent,
            "Show me books by Stephen King")
        print("=== BOOKS BY AUTHOR ===")
        print(result.final_output)

        result = await Runner.run(
            agent,
            "Group books by genre")
        print("=== AGGREGATE BY GENRE ===")
        print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())