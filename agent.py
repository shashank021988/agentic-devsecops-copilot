#!/usr/bin/env python3
"""
LangGraph Multi-Agent SRE Swarm
Supervisor -> Triage Agent -> Runbook RAG Agent -> GitOps Agent
"""

import os
import json
from typing import TypedDict, Annotated, Sequence
import operator

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from tools.kubernetes_tools import k8s_tools
from tools.azure_monitor_tools import azure_tools
from tools.gitops_tools import gitops_tools
from rag.runbook_indexer import search_runbooks

from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)

# ---- State -----
class SREState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    alert_payload: dict
    incident_summary: str
    runbook_steps: list
    fix_pr_url: str
    resolved: bool


# ---- Agents -----
SUPERVISOR_PROMPT = """You are the SRE Supervisor Agent. You receive incident alerts and coordinate
the triage, runbook lookup, and GitOps remediation agents. Route the task appropriately
and synthesize a final resolution report. Be concise and technical."""

TRIAGE_PROMPT = """You are the Triage Agent. Use MCP tools to inspect live Kubernetes pod status,
node health, deployment replicas, and recent logs. Produce a structured incident summary
with root cause hypothesis, affected services, and severity level (P1-P4)."""

RUNBOOK_PROMPT = """You are the Runbook RAG Agent. Given an incident summary, search the vector
runbook database for matching remediation procedures. Return step-by-step fix instructions."""

GITOPS_PROMPT = """You are the GitOps Agent. Given runbook steps and incident details, create
a GitHub Pull Request with the Terraform or Helm patch. Include Infracost diff in the PR body.
Always target the 'hotfix' branch from 'main'. Be precise and never break prod."""


def triage_agent(state: SREState) -> SREState:
    all_tools = k8s_tools + azure_tools
    triage_llm = llm.bind_tools(all_tools)
    alert = state["alert_payload"]
    messages = [
        SystemMessage(content=TRIAGE_PROMPT),
        HumanMessage(content=f"Alert received: {json.dumps(alert, indent=2)}\nInvestigate and summarize the incident.")
    ]
    response = triage_llm.invoke(messages)
    return {**state, "incident_summary": response.content, "messages": messages + [response]}


def runbook_agent(state: SREState) -> SREState:
    results = search_runbooks(state["incident_summary"], top_k=3)
    runbook_llm = llm.bind_tools(gitops_tools)
    messages = [
        SystemMessage(content=RUNBOOK_PROMPT),
        HumanMessage(content=f"Incident: {state['incident_summary']}\nRunbooks found: {json.dumps(results, indent=2)}")
    ]
    response = runbook_llm.invoke(messages)
    return {**state, "runbook_steps": results, "messages": state["messages"] + messages + [response]}


def gitops_agent(state: SREState) -> SREState:
    gitops_llm = llm.bind_tools(gitops_tools)
    messages = [
        SystemMessage(content=GITOPS_PROMPT),
        HumanMessage(content=f"Incident: {state['incident_summary']}\nRunbook steps: {state['runbook_steps']}\nCreate a hotfix PR.")
    ]
    response = gitops_llm.invoke(messages)
    return {**state, "fix_pr_url": response.content, "resolved": True, "messages": state["messages"] + [response]}


# ---- Graph -----
workflow = StateGraph(SREState)
workflow.add_node("triage", triage_agent)
workflow.add_node("runbook", runbook_agent)
workflow.add_node("gitops", gitops_agent)
workflow.add_node("tools", ToolNode(k8s_tools + azure_tools + gitops_tools))

workflow.set_entry_point("triage")
workflow.add_edge("triage", "runbook")
workflow.add_edge("runbook", "gitops")
workflow.add_edge("gitops", END)

graph = workflow.compile()

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI, Request
    app = FastAPI(title="Agentic SRE Copilot")

    @app.post("/webhook/alert")
    async def handle_alert(request: Request):
        payload = await request.json()
        initial_state = SREState(
            messages=[], alert_payload=payload,
            incident_summary="", runbook_steps=[],
            fix_pr_url="", resolved=False
        )
        result = graph.invoke(initial_state)
        return {"status": "resolved" if result["resolved"] else "pending", "pr_url": result["fix_pr_url"]}

    uvicorn.run(app, host="0.0.0.0", port=8001)
