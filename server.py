#!/usr/bin/env python3
"""
MCP Server: Exposes live Kubernetes telemetry and Azure Monitor metrics
as Model Context Protocol (MCP) tools for LangGraph agents.
"""

import os
import json
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from kubernetes import client, config
from azure.identity import DefaultAzureCredential
from azure.monitor.query import MetricsQueryClient
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP("devsecops-copilot")
app = FastAPI(title="DevSecOps Copilot MCP Server")


def get_k8s_client():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api()


@mcp.tool()
def get_pod_status(namespace: str = "default", label_selector: str = "") -> dict:
    """Get real-time status of Kubernetes pods in a namespace."""
    v1, _ = get_k8s_client()
    pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
    result = []
    for pod in pods.items:
        result.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "conditions": [
                {"type": c.type, "status": c.status, "reason": c.reason}
                for c in (pod.status.conditions or [])
            ],
            "containers": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": str(cs.state),
                }
                for cs in (pod.status.container_statuses or [])
            ],
        })
    return {"pods": result, "total": len(result), "timestamp": datetime.utcnow().isoformat()}


@mcp.tool()
def get_node_health() -> dict:
    """Get health and resource pressure status of all Kubernetes nodes."""
    v1, _ = get_k8s_client()
    nodes = v1.list_node()
    result = []
    for node in nodes.items:
        conditions = {c.type: c.status for c in node.status.conditions}
        result.append({
            "name": node.metadata.name,
            "ready": conditions.get("Ready") == "True",
            "memory_pressure": conditions.get("MemoryPressure") == "True",
            "disk_pressure": conditions.get("DiskPressure") == "True",
            "pid_pressure": conditions.get("PIDPressure") == "True",
            "allocatable": node.status.allocatable,
            "capacity": node.status.capacity,
        })
    return {"nodes": result, "timestamp": datetime.utcnow().isoformat()}


@mcp.tool()
def get_deployment_status(namespace: str = "default") -> dict:
    """Get rollout status and replica health of all Deployments."""
    _, apps_v1 = get_k8s_client()
    deployments = apps_v1.list_namespaced_deployment(namespace)
    result = []
    for d in deployments.items:
        result.append({
            "name": d.metadata.name,
            "desired_replicas": d.spec.replicas,
            "available_replicas": d.status.available_replicas or 0,
            "ready_replicas": d.status.ready_replicas or 0,
            "unavailable_replicas": d.status.unavailable_replicas or 0,
            "healthy": d.status.available_replicas == d.spec.replicas,
        })
    return {"deployments": result, "timestamp": datetime.utcnow().isoformat()}


@mcp.tool()
def get_pod_logs(namespace: str, pod_name: str, tail_lines: int = 100) -> dict:
    """Fetch recent logs from a specific pod for incident analysis."""
    v1, _ = get_k8s_client()
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name, namespace=namespace, tail_lines=tail_lines, timestamps=True
        )
        return {"pod": pod_name, "namespace": namespace, "logs": logs, "lines": tail_lines}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_azure_metric(
    resource_id: str,
    metric_names: list,
    hours: int = 1
) -> dict:
    """Query Azure Monitor metrics for a given resource over the last N hours."""
    credential = DefaultAzureCredential()
    client_az = MetricsQueryClient(credential)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    result = client_az.query_resource(
        resource_id,
        metric_names=metric_names,
        timespan=(start_time, end_time),
        granularity=timedelta(minutes=5),
    )
    metrics = {}
    for m in result.metrics:
        metrics[m.name] = [
            {"timestamp": str(dp.timestamp), "average": dp.average}
            for ts in m.timeseries
            for dp in ts.data
            if dp.average is not None
        ]
    return {"resource_id": resource_id, "metrics": metrics, "period_hours": hours}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("MCP_PORT", 8000)))
