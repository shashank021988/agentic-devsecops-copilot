from langchain.tools import tool
import httpx, os

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

@tool
def query_azure_metrics(resource_id: str, metric: str, hours: int = 1) -> str:
    """Query Azure Monitor metrics for a resource over the past N hours."""
    r = httpx.post(f"{MCP_URL}/tools/get_azure_metric",
                   json={"resource_id": resource_id, "metric_names": [metric], "hours": hours}, timeout=20)
    return r.text

azure_tools = [query_azure_metrics]
