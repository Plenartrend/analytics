import asyncio
import logging
import time

from ..config.config import HashrrConfig, NodeInfo

LOGGER = logging.getLogger("hashrr")


class Hashrr:
    def __init__(self, config: HashrrConfig):
        self._heartbeat_task = None
        self.config: HashrrConfig = config
        self.node_info: NodeInfo | None = None
        self.stop_event: asyncio.Event = asyncio.Event()

    async def connect(self):
        LOGGER.info("Hashrr running.")
        id = await self.config.register_callback()

        node_info = await self.config.get_my_node_callback(id)
        LOGGER.info("Node info: %s", node_info)

        self.node_info = node_info

        async def heartbeat():
            interval = 10.0
            loop = asyncio.get_running_loop()
            next_time = loop.time()
            send_fn = self.config.send_heartbeat_callback

            while not self.stop_event.is_set():
                # Call send_heartbeat_callback correctly whether it's async or sync
                if asyncio.iscoroutinefunction(send_fn):
                    await send_fn(node_info.id)
                else:
                    await loop.run_in_executor(None, send_fn, node_info.id)

                # schedule next run at fixed interval (measured with monotonic clock)
                next_time += interval
                sleep_for = next_time - loop.time()
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)

        self._heartbeat_task = asyncio.create_task(heartbeat())

    async def get_distributed_key(self) -> (int, int, int):
        nodes = await self.config.get_all_running_nodes_callback()
        sorted_nodes = sorted(nodes, key=lambda node: node.timestamp + node.id)
        for index, node in enumerate(sorted_nodes):
            if node.id == self.node_info.id:
                return index, len(sorted_nodes), self.node_info.id

        raise Exception("Node not found in the cluster.")

    async def stop(self):
        LOGGER.info("Hashrr stopping.")
        self.stop_event.set()
        if self.node_info:
            await self.config.unregister_callback(self.node_info.id)

    async def cleanup(self):
        LOGGER.info("Hashrr cleaned up.")
        nodes = await self.config.get_all_nodes_callback()
        for node in nodes:
            LOGGER.info("Cleaning up node: %s", node)

            if node.last_heartbeat + self.config.heartbeat_timeout_seconds < int(time.time()):
                await self.config.unregister_callback(node.id)
