from typing import Any, Dict


def register_nodes_metadata() -> Dict[str, Any]:
    return {
        "nodes": ["nursing_simulation.webrtc_node:WebRTCNode"],
        "description": "Nodes from the nursing simulation package",
    }
