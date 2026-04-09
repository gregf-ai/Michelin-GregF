"""LangGraph agent: Plan → Research → Analyze workflow for financial Q&A."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.tools import ALL_TOOLS

# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior financial analyst specializing in the global tire industry.
You have access to tools that query pre-downloaded financial data for six major tire companies:
Michelin (MGDDY), Goodyear (GT), Bridgestone (BRDCY), Continental (CTTAY), Pirelli (PLLIF), and Sumitomo (SSUMY).

Your workflow:
1. PLAN: Think about what data you need to answer the question. Consider which tools to call.
2. RESEARCH: Call the relevant tools to gather data. You can call multiple tools.
3. ANALYZE: Synthesize the data into a clear, data-driven answer.

Guidelines:
- Always cite specific numbers from the data.
- When comparing companies, present data in a structured way (tables when appropriate).
- Use markdown formatting for clear presentation.
- If data is missing for a company, note it rather than guessing.
- Be concise but thorough. Prioritize actionable insights.
- When discussing returns (ROIC, ROE, ROA), explain what drives differences between companies.
- For transcript searches, quote relevant passages and preserve the transcript source label in the final answer.
- Prefer using full-history windows when useful; do not default to short windows unless requested.
- For complex comparisons, you can use the DuckDB SQL tool to compute aggregates and rankings.
- Never fabricate values. If conflicting evidence appears, call additional tools and reconcile it explicitly.
- Any claim based on transcripts must include a source citation in this format: [Transcript: Company Q# YYYY, call date YYYY-MM-DD].

Output contract:
- Start with a direct answer (1-2 sentences).
- Then provide evidence bullets with concrete values, periods, and company names.
- End with limitations/data gaps if relevant.
"""


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(model_name: str = "gpt-4o-mini", temperature: float = 0.1):
    """Build and compile the LangGraph agent."""
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def call_model(state: AgentState) -> dict:
        messages = state["messages"]
        # Inject system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    # Build graph
    graph = StateGraph(AgentState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# For testing from command line
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    app = build_graph()
    question = "Which tire brand gets the best return on capital?"
    result = app.invoke({
        "messages": [HumanMessage(content=question)]
    })
    print(result["messages"][-1].content)
