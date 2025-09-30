from agents import Agent, Runner, AsyncOpenAI, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_default_openai_api
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams, create_static_tool_filter, ToolFilterContext
from dotenv import load_dotenv
import os
import asyncio
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
external_client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/")

set_default_openai_client(external_client)
set_tracing_disabled(True)
set_default_openai_api("chat_completions")

model = OpenAIChatCompletionsModel(
    model = "gemini-2.0-flash",
    openai_client = external_client)


async def dynamic_filtering(context: ToolFilterContext,tool):
    print("Context",context)
    print("Tool",tool)
    print("tool.name.startwith",tool.name.startwith("mood"))
    return tool.name.startwith("mood")

async def my_first_agent():
    params_config = MCPServerStreamableHttpParams(url="http://127.0.0.1:8000/mcp")
    static_filtering = create_static_tool_filter(blocked_tool_names=["get_mood"],allowed_tool_names=["greeting"])
    async with MCPServerStreamableHttp(params=params_config, name="Hello_mcp", cache_tools_list = True,tool_filter=dynamic_filtering) as mcp_server:
        mcp_server.invalidate_tools_cache()
        await mcp_server.connect()
        

        prompts = await mcp_server.list_prompts()
        print("Available prompts\n",prompts)

        greet = await mcp_server.get_prompt("general_chat",arguments={"user_name" : "Usman"})



        agent = Agent(
            name = "Assistant",
            instructions = greet.messages[0].context.text,
            model = model,
            mcp_servers=[mcp_server])
        
        result =await Runner.run(
            agent,
            "whats the mood of Usman")
        print(result.final_output)

if __name__ == "__main__":
    asyncio.run(my_first_agent())