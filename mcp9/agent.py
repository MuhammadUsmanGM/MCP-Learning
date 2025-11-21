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

        result = await Runner.run(
            agent,
            "whats the weather in Lahore?")
        print(result.final_output)

        result = await Runner.run(
            agent,
            "whats the address for ip 103.186.136.10?")
        print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())