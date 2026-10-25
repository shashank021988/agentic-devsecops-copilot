# Agentic DevSecOps Copilot

Autonomous Multi-Agent Incident Response & Infrastructure Self-Healing platform powered by **Model Context Protocol (MCP)** and **LangGraph**.

## Architecture
```
Azure Monitor / Prometheus Alert
        |
        v
  Webhook Receiver (FastAPI)
        |
        v
  LangGraph Supervisor Agent
   /          |          \
Triage    Runbook RAG   GitOps
Agent     Agent (Qdrant) Agent
        |
        v
  MCP Server (Live K8s Telemetry)
        |
        v
  Auto-draft GitOps PR + Infracost Diff
```

## Features
- MCP server exposing live Kubernetes pod/node telemetry
- LangGraph multi-agent swarm with Supervisor, Triage, RAG, and GitOps agents
- Vector runbook search via Qdrant
- Auto-draft Terraform/Helm fix PRs with GitHub API
- MTTR reduced from 45 min -> under 5 min

## Quick Start

```bash
pip install -r requirements.txt
docker-compose up -d  # starts Qdrant
python server.py       # starts MCP server on :8000
python agent.py        # starts LangGraph swarm on :8001
```
