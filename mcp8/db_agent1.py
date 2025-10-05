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
    async with MCPServerStreamableHttp(params=params_config, name="Universal_MongoDB_Server", cache_tools_list = True) as mcp_server:
        mcp_server.invalidate_tools_cache()
        await mcp_server.connect()

        greet = await mcp_server.get_prompt("instructions")

        agent = Agent(
            name="Universal_MongoDB_Assistant",
            instructions=greet.messages[0].content.text,
            model=model,
            mcp_servers=[mcp_server]
        )
        result = await Runner.run(
            agent,
            "Show me all available databases")
        print("=== ALL DATABASES ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "List all collections in the Library database")
        print("=== COLLECTIONS ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Get information about the books collection if it exists")
        print("=== COLLECTION INFO ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Count all documents in the books collection located in the Library database?")
        print("=== COUNT BOOKS ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Query books collection for documents where genre: programming")
        print("=== QUERY FANTASY BOOKS ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Add a new document to book collection of the Library database: title: the Ultimate Hacking, author : George Orwell, year : 2005, genre : programming, available : true")
        print("=== ADD PRODUCT ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Query products collection for all documents")
        print("=== ALL PRODUCTS ===")
        print(result.final_output)
        print()

        result = await Runner.run(
            agent,
            "Group products by category")
        print("=== GROUP PRODUCTS BY CATEGORY ===")
        print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())