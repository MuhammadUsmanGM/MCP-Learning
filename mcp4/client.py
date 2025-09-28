import asyncio
from contextlib import AsyncExitStack
from pydantic import AnyUrl
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from typing import Any

class McpClient:
    def __init__(self, url):
        self.url = url
        self.stack = AsyncExitStack()
        self._sess = None

    async def list_tools(self):
        async with self.session as session:
            response = (await session.list_tools()).tools
            return response

    async def __aenter__(self):
        read, write, _ = await self.stack.enter_async_context(
            streamablehttp_client(self.url)
        )
        self._sess = await self.stack.enter_async_context(ClientSession(read, write))
        await self._sess.initialize()
        return self

    async def __aexit__(self, *args):
        await self.stack.aclose()

    async def list_tools(self):
        return (await self._sess.list_tools()).tools

    async def list_resources(self) -> list[types.Resource]:
        result = await self._sess.list_resources()
        return result.resources
    async def read_resources(self,uri:AnyUrl)->types.ReadResourceResult:
        assert self._sess, "Session not avaiable."
        _url = AnyUrl(uri)
        result = await self._sess.read_resource(uri)
        resource = result.contents[0]
        return resource


async def main():
    async with McpClient("http://127.0.0.1:8000/mcp") as client:
        # tools = await client.list_tools()
        # print("Available tools:", tools)

        # resources = await client.list_resources()
        # print(resources, "Resources")
        read_resources = await client.read_resources("docs://documents")
        print("Read Resources",read_resources)

asyncio.run(main())


