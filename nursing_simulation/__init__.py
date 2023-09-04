from typing import Any, Dict


def register_nodes_metadata() -> Dict[str, Any]:
    return {
        "nodes": [
            "nursing_simulation.fastapi_server_node:FastAPIVideoNode",
        ],
        "description": "Nodes from the nursing simulation package",
    }
