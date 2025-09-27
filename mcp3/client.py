from mcp import ClientSession
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from contextlib import AsyncExitStack
class McpClient:
    def __init__(self,url):
        self.url = url
        self.stack = AsyncExitStack()
        self._sess = None

    async def list_tools(self):
        async with self.session as session:
            response = (await session.list_tools()).tools
            return response
    async def __aenter__(self):
        read,write, _ = await self.stack.enter_async_context(
            streamablehttp_client(self.url)
        )
        self._sess = await self.stack.enter_async_context(
            ClientSession(read,write)
        )
        await self._sess.initialize()
        return self
    async def __aexit__(self,*args):
        await self.stack.aclose()
    async def list_tools(self):
        return (await self._sess.list_tools()).tools
    async def call_tool(self,tool_name,*args,**kwargs):
        return await self._sess.call_tool(tool_name, arguments=kwargs)


async def main():
    async with McpClient("http://127.0.0.1:8000/mcp") as client:
        tools = await client.list_tools()
        print("Available tools:", tools)

        result = await client.call_tool("get_weather", city="Lahore")
        print("Weather result:", result)
        result = await client.call_tool("get_greeting", name="Usman")
        print("Greeting result:", result)

asyncio.run(main())


# import asyncio
# from contextlib import AsyncExitStack, asynccontextmanager

# @asynccontextmanager
# async def make_connection(name):
#     print("Connecting...${name}")
#     yield name
#     print("COnnected...${name}")

# async def main():
#     async with make_connection("A") as a:
#         print("Using connection ${a}")

# asyncio.run(main())

# async def get_connection(name):
#     class ctx():
#         async def __aenter__(self):
#             print(f"Connecting...${name}")
#             return name
#         async def __aexit__(self, exc_type, exc, tb):
#             print(f"Connected!${name}")
#     return ctx()

# # async def main():
# #     async with await get_connection("A") as a:
# #         print(f"Using connection {a}")


# async def main():
#     async with AsyncExitStack() as stack:
#         a = await stack.enter_async_context(await get_connection("A"))
#         if a == "A":
#             b = await stack.enter_async_context(await get_connection("B"))
#             print(f"Using connection: {a} and {b}")
        
#         async def customCleanup():
#             print("Custom cleanup logic here")
#         stack.push_async_callback(customCleanup)
#         print(f"Doing work with {a} and maybe {locals().get('b')}")
#         await asyncio.sleep(1)
# asyncio.run(main())
# -----------------------------------------
# import requests

# URL = "http://127.0.0.1:8000"
# PAYLOAD = {
#     'jsonrpc': "2.0",
#     "method":"tools/list",
#     "params":{},
#     "id":1
# }

# HEADERS = {
#     "Accept":"application/json,text/event-stream",
#     "Content-Type":"application/json"
# }

# response = requests.post(URL,json=PAYLOAD,headers=HEADERS,stream=True)
# print(response.text)

# for line in response.iter_lines():
#     if line:
#         print(line.decode('UFT-8'))

# ---------------------------------------------