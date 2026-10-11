"""Exercise a packaged MCP executable without moving the mouse or capturing screens."""
import asyncio
from datetime import timedelta
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    async with asyncio.timeout(60):
        async with stdio_client(StdioServerParameters(command=sys.argv[1])) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
                await client.initialize()
                response = await client.list_tools()
                if not response.tools: raise RuntimeError('Empty MCP tool catalog')
                print(json.dumps({'packaged_mcp': 'passed', 'tools': [t.name for t in response.tools]}))

if __name__ == '__main__': asyncio.run(main())
