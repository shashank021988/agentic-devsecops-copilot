from langchain.tools import tool
import httpx, os

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

@tool
def check_pod_status(namespace: str = "default") -> str:
    """Check the status of all pods in a Kubernetes namespace via MCP."""
    r = httpx.post(f"{MCP_URL}/tools/get_pod_status", json={"namespace": namespace}, timeout=15)
    return r.text

@tool
def check_node_health() -> str:
    """Check health and resource pressure on all Kubernetes nodes via MCP."""
    r = httpx.post(f"{MCP_URL}/tools/get_node_health", json={}, timeout=15)
    return r.text

@tool
def get_deployment_health(namespace: str = "default") -> str:
    """Check replica counts and availability for all Deployments via MCP."""
    r = httpx.post(f"{MCP_URL}/tools/get_deployment_status", json={"namespace": namespace}, timeout=15)
    return r.text

@tool
def fetch_pod_logs(namespace: str, pod_name: str) -> str:
    """Fetch the last 100 log lines from a specific Kubernetes pod."""
    r = httpx.post(f"{MCP_URL}/tools/get_pod_logs",
                   json={"namespace": namespace, "pod_name": pod_name, "tail_lines": 100}, timeout=20)
    return r.text

k8s_tools = [check_pod_status, check_node_health, get_deployment_health, fetch_pod_logs]
