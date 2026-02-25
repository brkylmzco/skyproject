from __future__ import annotations

import asyncio
import orjson as json
import logging
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, Dict

import aiofiles

from skyproject.core.config import LOGS_DIR, Config
from skyproject.shared.models import Message


logger = logging.getLogger(__name__)

MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


class ResizableQueue(asyncio.Queue):
    """A custom asyncio queue that allows dynamic resizing safely."""

    def __init__(self, maxsize: int = 0):
        super().__init__(maxsize=maxsize)
        self._historical_load = deque(maxlen=100)

    def resize(self, new_maxsize: int) -> None:
        """Resize the queue safely."""
        self._maxsize = new_maxsize

    def record_load(self, load: int) -> None:
        """Record the current load of the queue."""
        self._historical_load.append(load)

    def average_load(self) -> float:
        """Calculate the average load from historical data."""
        return sum(self._historical_load) / len(self._historical_load) if self._historical_load else 0


class MessageBus:
    """Async message bus enabling PM AI and IrgatAI to communicate."""

    def __init__(self):
        self._queues: Dict[str, ResizableQueue[Message]] = {
            "pm": ResizableQueue(maxsize=Config.MAX_QUEUE_SIZE),
            "irgat": ResizableQueue(maxsize=Config.MAX_QUEUE_SIZE),
        }
        self._handlers: Dict[str, list[MessageHandler]] = defaultdict(list)
        self._history: list[Message] = []
        self._log_file = LOGS_DIR / "messages.jsonl"
        self._acknowledgments: dict[str, asyncio.Event] = {}
        self._adjustment_task: Optional[asyncio.Task] = None
        self._start_adjustment_task()
        asyncio.create_task(self.monitor_message_flow())

    async def send(self, message: Message) -> None:
        """Send a message to the target's queue."""
        self._history.append(message)
        await self._log_message(message)

        target_queue = self._queues.get(message.receiver)
        if target_queue:
            await self._handle_backpressure(target_queue, message)
            self._acknowledgments[message.id] = asyncio.Event()
            asyncio.create_task(self._wait_for_acknowledgment(message))

        for handler in self._handlers.get(message.msg_type, []):
            asyncio.create_task(handler(message))

    async def receive(self, receiver: str, timeout: float = 30.0) -> Optional[Message]:
        """Wait for a message from the queue."""
        queue = self._queues.get(receiver)
        if not queue:
            return None
        try:
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            await self.acknowledge(message.id)
            return message
        except asyncio.TimeoutError:
            return None

    def subscribe(self, msg_type: str, handler: MessageHandler) -> None:
        """Subscribe to a specific message type."""
        self._handlers[msg_type].append(handler)

    async def receive_all(self, receiver: str) -> list[Message]:
        """Drain all pending messages for a receiver."""
        queue = self._queues.get(receiver)
        if not queue:
            return []
        messages = []
        while not queue.empty():
            try:
                message = queue.get_nowait()
                await self.acknowledge(message.id)
                messages.append(message)
            except asyncio.QueueEmpty:
                break
        return messages

    def get_history(self, limit: int = 50) -> list[Message]:
        return self._history[-limit:]

    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge receipt of a message."""
        if message_id in self._acknowledgments:
            self._acknowledgments[message_id].set()

    async def _wait_for_acknowledgment(self, message: Message, timeout: float = 30.0) -> None:
        """Wait for acknowledgment of a message with a retry mechanism."""
        max_retries = Config.MAX_RETRIES
        for attempt in range(max_retries):
            try:
                await asyncio.wait_for(self._acknowledgments[message.id].wait(), timeout=timeout)
                logger.info("Message %s acknowledged successfully.", message.id)
                del self._acknowledgments[message.id]  # Cleanup ack event
                return
            except asyncio.TimeoutError:
                logger.warning("Message %s not acknowledged, retrying %d/%d...", message.id, attempt + 1, max_retries)
                if attempt < max_retries - 1:  # Avoid extra send on last attempt
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    await self.send(message)  # Retry sending the message
        logger.error("Message %s failed to be acknowledged after %d retries.", message.id, max_retries)

    async def _handle_backpressure(self, queue: ResizableQueue[Message], message: Message) -> None:
        """Handle backpressure by waiting for space in the queue."""
        while queue.full():
            logger.warning("Queue for %s is full, waiting for space...", message.receiver)
            await asyncio.sleep(1)
        await queue.put(message)

    async def _log_message(self, message: Message) -> None:
        try:
            async with aiofiles.open(self._log_file, "a") as f:
                await f.write(json.dumps(message.model_dump_dict()) + "\n")
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to log message %s: %s", message.id, e)

    async def monitor_message_flow(self) -> None:
        """Monitor message flow and log statistics."""
        while True:
            await asyncio.sleep(60)  # Log every minute
            pending_ack_count = len(self._acknowledgments)
            logger.info("Currently %d messages pending acknowledgment.", pending_ack_count)

            for receiver, queue in self._queues.items():
                delay_threshold = Config.MAX_QUEUE_SIZE * 0.8
                if queue.qsize() > delay_threshold:
                    logger.warning("Potential bottleneck detected for %s: %d messages in queue.", receiver, queue.qsize())

    def _start_adjustment_task(self) -> None:
        """Start the task that adjusts queue sizes."""
        if self._adjustment_task is None:
            self._adjustment_task = asyncio.create_task(self.adjust_queue_sizes())

    async def adjust_queue_sizes(self) -> None:
        """Adjust queue sizes based on dynamic conditions."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                for receiver, queue in self._queues.items():
                    queue.record_load(queue.qsize())
                    average_load = queue.average_load()

                    if average_load > queue.maxsize * 0.8:
                        new_size = min(queue.maxsize * 2, Config.MAX_QUEUE_SIZE * 10)
                        logger.info("Increasing queue size for %s to %d.", receiver, new_size)
                        queue.resize(new_size)
                    elif average_load < queue.maxsize * 0.2 and queue.maxsize > Config.MAX_QUEUE_SIZE:
                        new_size = max(queue.maxsize // 2, Config.MAX_QUEUE_SIZE)
                        logger.info("Decreasing queue size for %s to %d.", receiver, new_size)
                        queue.resize(new_size)
        except asyncio.CancelledError:
            logger.info("Queue size adjustment task was cancelled.")