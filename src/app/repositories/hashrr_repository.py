from hashrr.config.config import NodeInfo
from sqlalchemy import and_, exists, func, select, text
from sqlalchemy.orm import aliased

from ..model.model import HashrrHeartbeat, HashrrInstance
from ..utils.db import get_db


async def register_callback():
    async with get_db() as db:
        instance = HashrrInstance()
        heartbeat = HashrrHeartbeat(instance=instance)

        db.add_all([instance, heartbeat])
        await db.commit()

        return instance.id


async def send_heartbeat_callback(id: int):
    async with get_db() as db:
        heartbeat = HashrrHeartbeat(hashrr_instance_id=id)
        db.add(heartbeat)
        try:
            await db.commit()
            await db.refresh(heartbeat)
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Failed to send heartbeat: {e}") from e


async def unregister_callback(id: int):
    async with get_db() as db:
        instance = await db.get(HashrrInstance, id)
        if instance:
            await db.delete(instance)
            await db.commit()


async def get_my_node_callback(id: int) -> NodeInfo:
    async with get_db() as db:
        instance = await db.get(HashrrInstance, id)
        if not instance:
            raise ValueError(f"Instance with id {id} not found.")

        last_heartbeat = (
            await db.execute(
                select(HashrrHeartbeat)
                .where(HashrrHeartbeat.hashrr_instance_id == id)
                .order_by(HashrrHeartbeat.heartbeat.desc())
                .limit(1)
            )
        ).scalar_one()

        if not last_heartbeat:
            raise ValueError(f"No heartbeat found for instance id {id}.")

        return NodeInfo(
            id=instance.id,
            timestamp=int(instance.created_at.timestamp()),
            last_heartbeat=int(last_heartbeat.heartbeat.timestamp()),
        )


async def get_all_nodes_callback() -> list[NodeInfo]:
    async with get_db() as db:
        h1 = aliased(HashrrHeartbeat)
        h2 = aliased(HashrrHeartbeat)
        stmt = (
            select(HashrrInstance.id, HashrrInstance.created_at, h1.heartbeat.label("last_heartbeat"))
            .join(h1, h1.hashrr_instance_id == HashrrInstance.id)
            .where(
                ~exists(
                    select(1).where(
                        and_(
                            h2.hashrr_instance_id == h1.hashrr_instance_id,
                            h2.heartbeat > h1.heartbeat,
                        )
                    )
                )
            )
        )

        result = await db.execute(stmt)
        rows = result.all()
        nodes = [
            NodeInfo(
                id=row.id, timestamp=int(row.created_at.timestamp()), last_heartbeat=int(row.last_heartbeat.timestamp())
            )
            for row in rows
        ]
        return nodes


async def get_all_running_nodes_callback() -> list[NodeInfo]:
    async with get_db() as db:
        # heartbeat_timeout = func.now() - text("INTERVAL '30 seconds'")
        h1 = aliased(HashrrHeartbeat)
        h2 = aliased(HashrrHeartbeat)
        stmt = (
            select(HashrrInstance.id, HashrrInstance.created_at, h1.heartbeat.label("last_heartbeat"))
            .join(h1, h1.hashrr_instance_id == HashrrInstance.id)
            .where(
                ~exists(
                    select(1).where(
                        and_(
                            h2.hashrr_instance_id == h1.hashrr_instance_id,
                            h2.heartbeat > h1.heartbeat,
                        )
                    )
                ),
                h1.heartbeat + text("INTERVAL '30 seconds'") >= func.now(),
            )
        )

        result = await db.execute(stmt)
        rows = result.all()
        nodes = [
            NodeInfo(
                id=row.id, timestamp=int(row.created_at.timestamp()), last_heartbeat=int(row.last_heartbeat.timestamp())
            )
            for row in rows
        ]
        return nodes
