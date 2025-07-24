from google.adk.tools import BaseTool
from google.adk.types import ToolOutput
import asyncio
import json
import webbrowser
import sys
import traceback

# Import MCP client libraries (assuming they are installed in your virtual environment)
# Make sure these are accessible by your ADK project.
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent

class FinancialDataFetcherTool(BaseTool):
    """
    A tool to fetch various financial data (Net Worth, Credit Report, EPF, Mutual Funds)
    from a local MCP server, handling login interactions.
    """

    # 1. Define the tool's name – this is how the LLM will refer to it.
    name = "fetch_financial_data"

    # 2. Provide a clear description so the LLM knows when to use this tool.
    description = (
        "Fetches various financial data types (e.g., 'net_worth', 'credit_report', 'epf_details', 'mf_transactions') "
        "from a connected local MCP server. If a login is required, it will return a login URL "
        "for the user to complete the login externally."
    )

    # 3. Define the input schema (arguments) your tool expects.
    # The 'data_type' argument tells the tool what specific financial data to fetch.
    input_schema = {
        "type": "object",
        "properties": {
            "data_type": {
                "type": "string",
                "enum": ["net_worth", "credit_report", "epf_details", "mf_transactions"],
                "description": "The type of financial data to fetch (e.g., 'net_worth', 'credit_report')."
            }
        },
        "required": ["data_type"]
    }

    # --- Internal Helper: Adapted from your call_mcp_tool function ---
    # This helper no longer uses `input()` to block, instead it returns the login info.
    async def _call_mcp_tool_internal(self, session: ClientSession, tool_name_with_service_prefix: str, args: dict = {}) -> dict | str:
        bare_tool_name = tool_name_with_service_prefix.split(':')[-1]
        max_retries = 1 # We'll let the main tool logic handle retries after external login if needed.

        try:
            response: CallToolResult = await session.call_tool(bare_tool_name, args)
            parsed_json_content = None

            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                first_content = response.content[0]
                if isinstance(first_content, TextContent):
                    try:
                        parsed_json_content = json.loads(first_content.text)
                    except json.JSONDecodeError:
                        return first_content.text # Return raw text if not JSON
                else:
                    return first_content # Return non-text content as is
            else:
                return response # Return raw CallToolResult if no content

            # Handle login_required status: Return the status instead of blocking with input()
            if parsed_json_content and parsed_json_content.get("status") == "login_required":
                login_url = parsed_json_content.get("login_url")
                message = parsed_json_content.get("message")
                if login_url:
                    # Attempt to open browser on the server machine, but do not block the agent.
                    try:
                        webbrowser.open_new_tab(login_url)
                    except Exception:
                        pass # Ignore if browser cannot be opened automatically

                # Return a structured dictionary indicating login is required
                return {"status": "login_required", "login_url": login_url, "message": message}

            return parsed_json_content # Return the fetched data if not login_required

        except Exception as e:
            # Propagate exceptions as errors for the main _run method to catch
            raise ValueError(f"Failed to call MCP tool '{tool_name_with_service_prefix}': {e}")

    # --- Internal fetching functions: Adapted from your fetch_*_data functions ---
    # These call the internal helper and return its raw response.
    async def _fetch_net_worth_data_internal(self, session: ClientSession) -> dict | str:
        return await self._call_mcp_tool_internal(session, 'networth:fetch_net_worth', {})

    async def _fetch_credit_report_data_internal(self, session: ClientSession) -> dict | str:
        return await self._call_mcp_tool_internal(session, 'networth:fetch_credit_report', {})

    async def _fetch_epf_details_data_internal(self, session: ClientSession) -> dict | str:
        return await self._call_mcp_tool_internal(session, 'networth:fetch_epf_details', {})

    async def _fetch_mf_transactions_data_internal(self, session: ClientSession) -> dict | str:
        return await self._call_mcp_tool_internal(session, 'networth:fetch_mf_transactions', {})

    # --- Main execution method for the ADK tool ---
    async def _run(self, data_type: str) -> ToolOutput:
        # **IMPORTANT**: Update this URL to match your actual MCP server's stream endpoint.
        mcp_stream_url = "http://localhost:8080/mcp/stream"

        try:
            # Connect to the MCP streamable HTTP client and create a ClientSession
            async with streamablehttp_client(mcp_stream_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # Call the appropriate internal fetch function based on the requested data_type
                    if data_type == "net_worth":
                        raw_response = await self._fetch_net_worth_data_internal(session)
                    elif data_type == "credit_report":
                        raw_response = await self._fetch_credit_report_data_internal(session)
                    elif data_type == "epf_details":
                        raw_response = await self._fetch_epf_details_data_internal(session)
                    elif data_type == "mf_transactions":
                        raw_response = await self._fetch_mf_transactions_data_internal(session)
                    else:
                        # Handle invalid data_type requests from the LLM
                        return ToolOutput(
                            raw_output=f"Invalid data_type requested: {data_type}. Supported types are: net_worth, credit_report, epf_details, mf_transactions.",
                            display_text="Invalid financial data type provided.",
                            is_error=True
                        )

                    # Check if the internal call returned a login_required status
                    if isinstance(raw_response, dict) and raw_response.get("status") == "login_required":
                        login_url = raw_response.get("login_url", "No URL provided.")
                        message = raw_response.get("message", "Login required to proceed.")
                        # Return an error ToolOutput to the agent, prompting user action
                        return ToolOutput(
                            raw_output=json.dumps(raw_response, indent=2),
                            display_text=(
                                f"Access to {data_type.replace('_', ' ')} requires login. "
                                f"Please visit this URL to complete login in your browser: {login_url}. "
                                f"After logging in successfully, you can ask me to try fetching the data again."
                            ),
                            is_error=True
                        )

                    # If no login is required, process and return the fetched data
                    if raw_response:
                        summary_text = f"Successfully fetched {data_type.replace('_', ' ')} data."
                        # You can add more detailed summary parsing here if needed,
                        # similar to how your original script parsed and printed specific fields.
                        if data_type == "net_worth" and isinstance(raw_response, dict) and 'netWorthResponse' in raw_response:
                            total_value_units = raw_response['netWorthResponse']['totalNetWorthValue']['units']
                            total_value_nanos = raw_response['netWorthResponse']['totalNetWorthValue'].get('nanos', 0)
                            total_value = float(total_value_units) + (total_value_nanos / 1_000_000_000)
                            summary_text = f"Total Net Worth: {total_value:.2f} INR."
                        elif data_type == "credit_report" and isinstance(raw_response, dict) and 'creditReports' in raw_response and len(raw_response['creditReports']) > 0:
                            score = raw_response['creditReports'][0]['creditReportData']['score']['bureauScore']
                            summary_text = f"Credit Score: {score}."
                        elif data_type == "epf_details" and isinstance(raw_response, dict) and 'uanAccounts' in raw_response and len(raw_response['uanAccounts']) > 0:
                            total_balance = float(raw_response['uanAccounts'][0]['rawDetails'].get('overall_pf_balance', {}).get('current_pf_balance', 0))
                            summary_text = f"EPF Total Balance: {total_balance:.2f} INR."
                        elif data_type == "mf_transactions" and isinstance(raw_response, dict) and 'transactions' in raw_response:
                            summary_text = f"Fetched {len(raw_response['transactions'])} mutual fund transactions."

                        return ToolOutput(
                            raw_output=json.dumps(raw_response, indent=2),
                            display_text=summary_text
                        )
                    else:
                        # Case where response is empty but not an error or login_required
                        return ToolOutput(
                            raw_output="No data available or accounts not connected.",
                            display_text=f"No {data_type.replace('_', ' ')} data available or accounts might not be connected to MCP.",
                            is_error=True
                        )

        except Exception as e:
            # Catch any high-level errors during MCP connection or general execution
            return ToolOutput(
                raw_output=f"An unexpected error occurred while fetching {data_type}: {e}\n{traceback.format_exc()}",
                display_text=f"An error occurred while trying to fetch {data_type.replace('_', ' ')}. Please check the MCP server and network connection. Error: {e}",
                is_error=True
            )