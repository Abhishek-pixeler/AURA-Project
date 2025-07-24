from google.adk.agents import Agent
from google.adk.llms import Message
# Import your new tool
from .tools.financial_data_tool import FinancialDataFetcherTool # Adjust path if your tool file is elsewhere

class MyCustomAgent(Agent):
    """
    My ADK agent that can fetch various financial data from a local MCP server.
    """

    def __init__(self):
        super().__init__()
        # Initialize and register your new tool here
        self.register_tool(FinancialDataFetcherTool())

    async def _on_message(self, message: Message) -> Message:
        # This is where your agent's core logic will be.
        # The LLM now has access to the 'fetch_financial_data' tool.
        # You will prompt the LLM to use this tool when needed.

        # Example: If the user asks for financial data, the LLM will decide
        # to call your tool based on the tool's description and input_schema.
        # Your agent's response generation logic would go here.
        # For a basic agent, you might just pass the message to the LLM.
        response = await self.llm.generate_response(
            messages=[message],
            tools=self.get_registered_tools() # Ensure tools are passed to the LLM
        )
        return response