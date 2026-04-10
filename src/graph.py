"""LangGraph agent with explicit intent routing before tool selection."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.tools import ALL_TOOLS, TOOL_REGISTRY

# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    route: str


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
- Do not speculate about future events or unavailable years. If transcript coverage is missing, state the available years returned by tools.
- Any claim based on transcripts must include a source citation in this format: [Transcript: Company Q# YYYY, call date YYYY-MM-DD].

Output contract:
- Start with a direct answer (1-2 sentences).
- Then provide evidence bullets with concrete values, periods, and company names.
- End with limitations/data gaps if relevant.
"""


def _classify_route(text: str) -> str:
    """Heuristic router for selecting the most relevant tool subset."""
    q = (text or "").lower()

    patent_terms = [
        "patent", "usp to", "uspto", "filing", "application", "claims", "invention", "ip",
    ]
    transcript_terms = [
        "transcript", "earnings call", "call", "management commentary", "quote", "conference call",
        "said", "guidance", "prepared remarks",
    ]
    financial_terms = [
        "income statement", "revenue", "margin", "roic", "roe", "roa", "cash flow", "ebitda",
        "dividend", "stock", "ratio", "profit", "balance sheet",
    ]

    has_patent = any(term in q for term in patent_terms)
    has_transcript = any(term in q for term in transcript_terms)
    has_financial = any(term in q for term in financial_terms)

    domains = sum([has_patent, has_transcript, has_financial])
    if domains >= 2:
        return "mixed"
    if has_patent:
        return "patent"
    if has_transcript:
        return "transcript"
    if has_financial:
        return "financial"
    return "mixed"


ROUTE_TO_TOOL_NAMES = {
    "financial": [
        "get_financials",
        "get_ratios",
        "get_stock_performance",
        "get_company_overview",
        "get_data_coverage",
        "query_financial_database",
    ],
    "transcript": [
        "search_transcripts",
        "search_news",
        "get_company_overview",
        "get_data_coverage",
        "query_financial_database",
    ],
    "patent": [
        "search_patent_filings",
        "get_company_overview",
        "get_data_coverage",
        "query_financial_database",
    ],
    "mixed": [tool.name for tool in ALL_TOOLS],
}


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(model_name: str = "gpt-4o-mini", temperature: float = 0.1):
    """Build and compile the LangGraph agent."""
    llm = ChatOpenAI(model=model_name, temperature=temperature)

    def route_query(state: AgentState) -> dict:
        latest_user = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                latest_user = str(msg.content)
                break
        route = _classify_route(latest_user)
        return {"route": route}

    def call_model(state: AgentState) -> dict:
        route = state.get("route", "mixed")
        tool_names = ROUTE_TO_TOOL_NAMES.get(route, ROUTE_TO_TOOL_NAMES["mixed"])
        selected_tools = [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]
        llm_with_tools = llm.bind_tools(selected_tools)

        messages = state["messages"]
        # Inject system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        route_hint = SystemMessage(
            content=(
                f"Routing decision: {route}. Preferred tools for this request: "
                f"{', '.join(tool_names)}. Use these tools unless additional evidence is strictly necessary."
            )
        )
        messages = messages + [route_hint]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    # Build graph
    graph = StateGraph(AgentState)

    graph.add_node("router", route_query)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.set_entry_point("router")
    graph.add_edge("router", "agent")
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
