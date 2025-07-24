from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent
import asyncio
import json
import sys
import os

async def call_mcp_tool_after_login(session, tool_name_with_service_prefix, args={}):
    bare_tool_name = tool_name_with_service_prefix.split(':')[-1]
    response: CallToolResult = await session.call_tool(bare_tool_name, args)
    if response.content and isinstance(response.content, list) and len(response.content) > 0:
        return json.loads(response.content[0].text)
    return None

async def main_data_fetching():
    try:
        with open("mcp_session.tmp", "r") as f:
            session_id = f.read().strip()
    except FileNotFoundError:
        print(json.dumps({"error": "Session file not found. Please run the login process first."}))
        return
        
    url = f"http://localhost:8080/mcp/stream?sessionId={session_id}"
    try:
        async with streamablehttp_client(url) as (read, write, _,):
            async with ClientSession(read, write) as session:
                await session.initialize()
                data = {
                    "net_worth": await call_mcp_tool_after_login(session, 'networth:fetch_net_worth'),
                    "credit_report": await call_mcp_tool_after_login(session, 'networth:fetch_credit_report'),
                    "epf_details": await call_mcp_tool_after_login(session, 'networth:fetch_epf_details'),
                    "mutual_fund_transactions": await call_mcp_tool_after_login(session, 'networth:fetch_mf_transactions'),
                }
                print(json.dumps(data, indent=2))
                os.remove("mcp_session.tmp")
    except Exception as e:
        print(json.dumps({"error": f"An error occurred during data fetching: {e}"}))

if __name__ == "__main__":
    asyncio.run(main_data_fetching())
