import asyncio
import json
import webbrowser
import os
from fastapi import FastAPI
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent

app = FastAPI()

# This helper function creates a new, clean session for every request.
async def get_mcp_session(session_id: str = None):
    url = "http://localhost:8080/mcp/stream"
    if session_id:
        url += f"?sessionId={session_id}"
    
    client = streamablehttp_client(url)
    read, write, _ = await client.__aenter__()
    session = ClientSession(read, write)
    await session.initialize()
    return session, client

@app.post("/start-login")
async def start_login():
    """This route creates a new session and triggers the login flow."""
    session, client = await get_mcp_session()
    try:
        response: CallToolResult = await session.call_tool('fetch_net_worth', {})
        if response.content and isinstance(response.content, list) and len(response.content) > 0:
            parsed_content = json.loads(response.content[0].text)
            if parsed_content.get("status") == "login_required":
                login_url = parsed_content.get("login_url")
                if login_url:
                    # Extract and save the session ID to a temporary file
                    session_id = login_url.split('sessionId=')[-1]
                    with open("mcp_session.tmp", "w") as f:
                        f.write(session_id)
                    webbrowser.open_new_tab(login_url)
                    return {"status": "success", "message": "Browser opened for login."}
        return {"status": "error", "message": "Failed to trigger login flow."}
    finally:
        # Always ensure the client connection is closed
        await client.__aexit__(None, None, None)

@app.get("/get-data")
async def get_data():
    """This route reads the session ID and reconnects to fetch data."""
    try:
        with open("mcp_session.tmp", "r") as f:
            session_id = f.read().strip()
    except FileNotFoundError:
        return {"error": "Session file not found. Please log in first."}, 404

    session, client = await get_mcp_session(session_id=session_id)
    try:
        async def call_tool(name):
            response: CallToolResult = await session.call_tool(name, {})
            return json.loads(response.content[0].text) if response.content else None
        
        data = {
            "net_worth": await call_tool('fetch_net_worth'),
            "credit_report": await call_tool('fetch_credit_report'),
            "epf_details": await call_tool('fetch_epf_details'),
            "mutual_fund_transactions": await call_tool('fetch_mf_transactions'),
        }
        return data
    finally:
        # Always ensure the client connection is closed and the temp file is removed
        await client.__aexit__(None, None, None)
        if os.path.exists("mcp_session.tmp"):
            os.remove("mcp_session.tmp")
