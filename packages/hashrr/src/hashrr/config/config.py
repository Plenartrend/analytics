from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class NodeInfo:
    id: int
    timestamp: int
    last_heartbeat: int


@dataclass
class HashrrConfig:
    register_callback: Callable[[], Awaitable[int]]
    send_heartbeat_callback: Callable[[int], Awaitable[None]]
    unregister_callback: Callable[[int], Awaitable[None]]
    get_my_node_callback: Callable[[int], Awaitable[NodeInfo]]
    get_all_nodes_callback: Callable[[], Awaitable[list[NodeInfo]]]
    get_all_running_nodes_callback: Callable[[], Awaitable[list[NodeInfo]]]

    heartbeat_interval_seconds: int = 10
    heartbeat_timeout_seconds: int = 30
