import asyncio
import json
import webbrowser
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent

async def main():
    """Handles the entire login and data fetch process in one go."""
    print("--- SCRIPT: Starting MCP connection... ---")
    try:
        async with streamablehttp_client("http://localhost:8080/mcp/stream") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("--- SCRIPT: Session initialized. Triggering login... ---")
                
                # Trigger the login flow
                response: CallToolResult = await session.call_tool('fetch_net_worth', {})
                if not (response.content and isinstance(response.content[0], TextContent)):
                    print(json.dumps({"error": "Failed to get response from server."}))
                    return

                parsed_content = json.loads(response.content[0].text)
                if parsed_content.get("status") != "login_required":
                    # If we don't need to log in, just print the data
                    print(json.dumps(parsed_content, indent=2))
                    return

                login_url = parsed_content.get("login_url")
                if not login_url:
                    print(json.dumps({"error": "Login required but no login URL provided."}))
                    return
                
                # --- The User Interaction Step ---
                print(f"--- SCRIPT: Opening browser at {login_url} ---")
                webbrowser.open_new_tab(login_url)
                
                # This is the crucial pause. The script will wait here.
                input("\n***** BROWSER OPENED *****\nPlease complete the login, then return to this terminal and press Enter to continue...")
                
                # --- The Data Fetching Step ---
                print("--- SCRIPT: Login complete. Fetching all data... ---")
                
                async def call_tool(name):
                    tool_response = await session.call_tool(name, {})
                    return json.loads(tool_response.content[0].text) if tool_response.content else None

                fetch_tasks = [
                    call_tool('fetch_net_worth'),
                    call_tool('fetch_credit_report'),
                    call_tool('fetch_epf_details'),
                    call_tool('fetch_mf_transactions'),
                    call_tool('fetch_stock_transactions'),
                    call_tool('fetch_bank_transactions'),
             ]
                results = await asyncio.gather(*fetch_tasks)
                all_data = {
                    "net_worth": results[0],
                    "credit_report": results[1],
                    "epf_details": results[2],
                    "mutual_fund_transactions": results[3],
                    "stock_transactions": results[4],
                    "bank_transactions": results[5],
                }
                
                # Print the final result for the agent to capture
                print(json.dumps(all_data, indent=2))

    except Exception as e:
        print(json.dumps({"error": f"An unhandled exception occurred: {e}"}))

if __name__ == "__main__":
    asyncio.run(main())
