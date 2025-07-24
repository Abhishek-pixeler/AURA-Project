from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent
import asyncio
import json
import sys
import traceback
import webbrowser
import time  # For a short delay

print("SCRIPT START: Initializing...")


# --- Helper function to call MCP tools ---
async def call_mcp_tool(session, tool_name_with_service_prefix, args={}):
    """
    Calls an MCP tool using the session.call_tool method.
    It extracts the bare tool name (e.g., 'fetch_net_worth' from 'networth:fetch_net_worth').
    Parses the CallToolResult to extract JSON content if available.
    Handles 'login_required' status by opening a browser and retrying.
    """
    bare_tool_name = tool_name_with_service_prefix.split(':')[-1]

    # Max retries to prevent infinite loops if login never succeeds
    max_retries = 2  # Allow one initial call + one retry after browser login
    retries = 0

    while retries < max_retries:
        try:
            print(
                f"DEBUG: Attempting to call tool '{bare_tool_name}' (originally '{tool_name_with_service_prefix}') with args: {args} (Retry: {retries}/{max_retries - 1})")
            response: CallToolResult = await session.call_tool(bare_tool_name, args)
            print(f"DEBUG: Raw response for '{bare_tool_name}':")
            print(response)

            parsed_json_content = None

            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                first_content = response.content[0]
                if isinstance(first_content, TextContent):
                    try:
                        parsed_json_content = json.loads(first_content.text)
                        print(f"DEBUG: Parsed JSON content for '{bare_tool_name}':")
                        print(json.dumps(parsed_json_content, indent=2))
                    except json.JSONDecodeError:
                        print(f"DEBUG: Content for '{bare_tool_name}' is not valid JSON, returning raw text.")
                        return first_content.text  # Return raw text if not JSON
                else:
                    print(f"DEBUG: First content for '{bare_tool_name}' is not TextContent, returning raw object.")
                    return first_content  # Return non-text content as is
            else:
                print(f"DEBUG: No content found in CallToolResult for '{bare_tool_name}'.")
                # If no content, it's possible it's just a success response with no data
                # We'll return the raw CallToolResult and let the calling function decide
                return response

            # --- Handle login_required status ---
            if parsed_json_content and parsed_json_content.get("status") == "login_required":
                login_url = parsed_json_content.get("login_url")
                message = parsed_json_content.get("message")

                if login_url:
                    print(f"\n***** IMPORTANT: LOGIN REQUIRED *****")
                    print(f"Please log in using the following URL in your browser:")
                    print(f"  --> {login_url}")
                    print(f"{message}\n")

                    try:
                        webbrowser.open_new_tab(login_url)
                        print("Attempted to open login URL in your default browser. Please complete the login there.")
                        input(
                            "Press Enter AFTER you have completed the login in your browser and it says 'Login Successful!'...")
                        print("Waiting a moment for session to update...")
                        await asyncio.sleep(2)  # Give a small delay for session state to propagate if needed
                        retries += 1  # Increment retry counter
                        continue  # Loop back to re-attempt the tool call with the same session
                    except Exception as browser_error:
                        print(f"Could not open browser automatically: {browser_error}")
                        print("Please manually copy and paste the URL into your browser.")
                        # Still prompt for enter, but without auto-open
                        input(
                            "Press Enter AFTER you have completed the login in your browser and it says 'Login Successful!'...")
                        print("Waiting a moment for session to update...")
                        await asyncio.sleep(2)
                        retries += 1
                        continue  # Loop back to re-attempt the tool call

            # If we reach here, either it was not login_required, or it was retried and now succeeded.
            return parsed_json_content

        except Exception as e:
            print(
                f"DEBUG EXCEPTION: An error occurred during session.call_tool for '{tool_name_with_service_prefix}' (or '{bare_tool_name}'):")
            traceback.print_exc(file=sys.stdout)
            # If an exception other than login_required occurs, propagate it
            raise ValueError(f"Failed to call tool {tool_name_with_service_prefix}: {e}")

    # If all retries fail, raise an error indicating it.
    raise ValueError(
        f"Failed to call tool {tool_name_with_service_prefix} after {max_retries} attempts due to persistent login requirement or other issue.")


# --- Fetching functions for specific data types ---
# Keep these as they were, but ensure they handle the case where
# call_mcp_tool might return the login_required dict *after* the prompt,
# in case the user doesn't complete login or max_retries is reached.
async def fetch_net_worth_data(session):
    print("Fetching Net Worth data...")
    try:
        response = await call_mcp_tool(session, 'networth:fetch_net_worth', {})

        # Check if the response is the 'login_required' dictionary, meaning login didn't fully succeed in this attempt
        if isinstance(response, dict) and response.get("status") == "login_required":
            print("Login still required for Net Worth. Cannot fetch data until successful login.")
            return  # Exit function as login isn't complete

        # Proceed with parsing if not 'login_required'
        if response and 'netWorthResponse' in response and 'totalNetWorthValue' in response['netWorthResponse']:
            total_value_units = response['netWorthResponse']['totalNetWorthValue']['units']
            total_value_nanos = response['netWorthResponse']['totalNetWorthValue'].get('nanos', 0)
            total_value = float(total_value_units) + (total_value_nanos / 1_000_000_000)
            print(f"Total Net Worth: {total_value:.2f} INR")
            if 'assetValues' in response['netWorthResponse']:
                print("Assets:", response['netWorthResponse']['assetValues'])
            else:
                print("No asset details available.")
        else:
            print("No net worth data available or accounts not connected. Please connect accounts.")
            if response:
                print(f"Raw response was not as expected: {json.dumps(response)}")
            else:
                print("Raw response was empty/None.")
    except Exception as e:
        print(f"Error fetching net worth: {e}")


# Apply similar login_required checks in fetch_credit_report_data, fetch_epf_details_data, fetch_mf_transactions_data

async def fetch_credit_report_data(session):
    print("Fetching Credit Report data...")
    try:
        response = await call_mcp_tool(session, 'networth:fetch_credit_report', {})
        if isinstance(response, dict) and response.get("status") == "login_required":
            print("Login still required for Credit Report. Cannot fetch data until successful login.")
            return
        if response and 'creditReports' in response and len(response['creditReports']) > 0:
            credit_data = response['creditReports'][0]['creditReportData']
            score = credit_data['score']['bureauScore']
            dob = credit_data['currentApplication']['currentApplicationDetails']['currentApplicantDetails'][
                'dateOfBirthApplicant']
            accounts = credit_data['creditAccount']['creditAccountDetails']
            print(f"Credit Score: {score}")
            print(f"Date of Birth: {dob}")
            print("Credit Accounts:", accounts)
        else:
            print("No credit score data available. Please connect credit profile.")
            if response:
                print(f"Raw response was not as expected: {json.dumps(response)}")
            else:
                print("Raw response was empty/None.")
    except Exception as e:
        print(f"Error fetching credit report: {e}")


async def fetch_epf_details_data(session):
    print("Fetching EPF Details data...")
    try:
        response = await call_mcp_tool(session, 'networth:fetch_epf_details', {})
        if isinstance(response, dict) and response.get("status") == "login_required":
            print("Login still required for EPF. Cannot fetch data until successful login.")
            return
        if response and 'uanAccounts' in response and len(response['uanAccounts']) > 0:
            epf_data = response['uanAccounts'][0]['rawDetails']
            total_balance = float(epf_data.get('overall_pf_balance', {}).get('current_pf_balance', 0))
            employee_share = float(
                epf_data.get('overall_pf_balance', {}).get('employee_share_total', {}).get('balance', 0))
            employer_share = float(
                epf_data.get('overall_pf_balance', {}).get('employer_share_total', {}).get('balance', 0))

            print(f"EPF Total Balance: {total_balance:.2f}")
            print(f"Employee Share: {employee_share:.2f}")
            print(f"Employer Share: {employer_share:.2f}")
        else:
            print("No EPF data available. Please link EPF account.")
            if response:
                print(f"Raw response was not as expected: {json.dumps(response)}")
            else:
                print("Raw response was empty/None.")
    except Exception as e:
        print(f"Error fetching EPF details: {e}")


async def fetch_mf_transactions_data(session):
    print("Fetching Mutual Fund Transactions data...")
    try:
        response = await call_mcp_tool(session, 'networth:fetch_mf_transactions', {})
        if isinstance(response, dict) and response.get("status") == "login_required":
            print("Login still required for Mutual Fund Transactions. Cannot fetch data until successful login.")
            return
        if response and 'transactions' in response and len(response['transactions']) > 0:
            transactions = response['transactions']
            print(f"Fetched {len(transactions)} mutual fund transactions.")
            if transactions:
                first_tx = transactions[0]
                tx_amount_units = first_tx.get('transactionAmount', {}).get('units', 0)
                tx_amount_nanos = first_tx.get('transactionAmount', {}).get('nanos', 0)
                actual_amount = float(tx_amount_units) + (tx_amount_nanos / 1_000_000_000)
                print(
                    f"First MF Transaction: Date={first_tx.get('transactionDate', 'N/A')}, Amount={actual_amount:.2f}, Type={first_tx.get('externalOrderType', 'N/A')}")
        else:
            print("No mutual fund transactions found.")
            if response:
                print(f"Raw response was not as expected: {json.dumps(response)}")
            else:
                print("Raw response was empty/None.")
    except Exception as e:
        print(f"Error fetching mutual fund transactions: {e}")


# --- Main data fetching orchestration ---
async def main_data_fetching():
    print("MAIN: Starting main_data_fetching...")
    try:
        print("MAIN: Attempting to connect to streamable_http client...")
        async with streamablehttp_client("http://localhost:8080/mcp/stream") as (
                read_stream,
                write_stream,
                _,
        ):
            print("MAIN: Streamable HTTP client connected.")
            print("MAIN: Attempting to create ClientSession...")
            async with ClientSession(
                    read_stream,
                    write_stream,
            ) as session:
                print("MAIN: ClientSession created. Initializing session...")
                await session.initialize()
                print("MCP session initialized successfully.")
                tools_info = await session.list_tools()
                print("Available tools:", tools_info)

                print("\n--- Inspecting ClientSession object attributes ---")
                print("dir(session):", dir(session))
                print("\nCallable attributes (methods) on session:")
                for attr_name in dir(session):
                    attr = getattr(session, attr_name)
                    if callable(attr) and not attr_name.startswith('_'):
                        print(f"  - {attr_name}")
                print("-------------------------------------------------")

                print("\nAttempting to fetch data with 'call_tool' method (using bare tool names)...")

                print("\n--- Fetching Net Worth ---")
                await fetch_net_worth_data(session)

                print("\n--- Fetching Credit Report ---")
                await fetch_credit_report_data(session)

                print("\n--- Fetching EPF Details ---")
                await fetch_epf_details_data(session)

                print("\n--- Fetching Mutual Fund Transactions ---")
                await fetch_mf_transactions_data(session)

    except Exception as e:
        print(f"An error occurred during main data fetching: {e}")
        traceback.print_exc(file=sys.stdout)


# --- Entry point ---
if __name__ == "__main__":
    print("ENTRY POINT: Running asyncio.run(main_data_fetching())...")
    asyncio.run(main_data_fetching())
    print("SCRIPT END: asyncio.run finished.")