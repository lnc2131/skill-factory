"""Start `{{name}} mcp` the way Claude Code does and call a tool over stdio."""

import os
import sys

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

EXE = os.path.join(os.path.dirname(sys.executable), "{{name}}")


def test_hello_over_stdio():
    async def go():
        async with Client(StdioServerParameters(command=EXE, args=["mcp"])) as c:
            tools = [t.name for t in (await c.list_tools()).tools]
            r = await c.call_tool("hello", {"name": "Lucas"})
            return tools, r.content[0].text

    tools, text = anyio.run(go)
    assert "hello" in tools
    assert text == "Hello, Lucas!"
