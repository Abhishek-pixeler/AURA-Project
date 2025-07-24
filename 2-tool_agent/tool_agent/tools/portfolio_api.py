# tools/portfolio_api.py

from google.adk.tools import FunctionTool, ToolContext
import subprocess
import sys
import json

def run_portfolio_flow(tool_context: ToolContext) -> str:
    """
    Manages fetching portfolio data. It first checks for cached data in the agent's
    state. If no data is found, it runs the interactive script to fetch new data,
    caches it, and then returns it.
    """
    # 1. Check the agent's memory (state) for existing data.
    if 'portfolio_data' in tool_context.state:
        print("--- TOOL: Found cached data. Returning from state. ---")
        # Return the cached data directly.
        return tool_context.state['portfolio_data']

    # 2. If no data is in memory, run the script to fetch it.
    print("--- TOOL: No cached data found. Running interactive script. ---")
    try:
        result = subprocess.run(
            [sys.executable, 'mcp_script.py'],
            capture_output=True, text=True, check=True, timeout=300
        )
        
        # 3. Store the newly fetched data in the agent's memory for next time.
        tool_context.state['portfolio_data'] = result.stdout
        
        return result.stdout
    except Exception as e:
        return f"Error: Failed to execute the main portfolio script. Details: {e}"

# This part remains the same.
portfolio_flow_tool = FunctionTool(func=run_portfolio_flow)

