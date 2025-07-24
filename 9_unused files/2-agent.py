# agents/agent.py

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import agent_tool
# This is the new, required import

# Import your specialist agent as before
from .portfolio_agent import portfolio_analysis_agent

load_dotenv()

# This is the key change: wrap the specialist agent in AgentTool
portfolio_tool = agent_tool.AgentTool(agent=portfolio_analysis_agent)

# Define the main "manager" agent
finance_orchestrator = Agent(
    name="FinanceOrchestrator",
    model="gemini-2.0-flash",
    description="A master financial assistant that can answer general questions or delegate portfolio analysis to a specialist.",
    
    instruction=(
        "You are the main financial assistant. For general questions, answer them directly. "
        "If the user asks about their portfolio, stock holdings, or finances, "
        "you must use the `PortfolioAnalysisAgent` tool to get the answer."
    ),
    
    
    
    # Now, give the orchestrator the wrapped AgentTool object
    tools=[
        portfolio_tool
    ]
)

# The root_agent is still the orchestrator
root_agent = finance_orchestrator
