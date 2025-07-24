from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent
import asyncio
import json
import webbrowser

async def main_login_trigger():
    print("LOGIN SCRIPT: Starting login process...")
    try:
        async with streamablehttp_client("http://localhost:8080/mcp/stream") as (read, write, _,):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response: CallToolResult = await session.call_tool('fetch_net_worth', {})
                if response.content and isinstance(response.content, list) and len(response.content) > 0:
                    first_content = response.content[0]
                    if isinstance(first_content, TextContent):
                        parsed_content = json.loads(first_content.text)
                        if parsed_content.get("status") == "login_required":
                            login_url = parsed_content.get("login_url")
                            if login_url:
                                session_id = login_url.split('sessionId=')[-1]
                                with open("mcp_session.tmp", "w") as f:
                                    f.write(session_id)
                                print(f"LOGIN SCRIPT: Saved session ID to mcp_session.tmp")
                                webbrowser.open_new_tab(login_url)
    except Exception as e:
        print(f"LOGIN SCRIPT ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main_login_trigger())
