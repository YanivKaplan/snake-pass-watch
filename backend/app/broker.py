"""A tiny in-process pub/sub used to drive Server-Sent Events.

Each SSE subscriber gets an :class:`asyncio.Queue`. Whenever active-game state
changes (publish, end, or prune), routers call :meth:`Broker.notify`, which wakes
every subscriber so it can re-read the store and emit a fresh snapshot.
"""

import asyncio


class Broker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def notify(self) -> None:
        """Signal all subscribers that active-game state changed (non-blocking)."""
        for queue in list(self._subscribers):
            queue.put_nowait(None)


# Process-wide singleton shared by the routers.
broker = Broker()
