import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from skyproject.core.communication import MessageBus, ResizableQueue
from skyproject.shared.models import Message
from skyproject.core.config import Config


@pytest.fixture
async def message_bus():
    return MessageBus()


@pytest.mark.asyncio
async def test_send_and_receive_message(message_bus: MessageBus):
    message = Message(id="1", sender="pm", receiver="irgat", msg_type="test", content={})

    await message_bus.send(message)
    received_message = await message_bus.receive("irgat")

    assert received_message.id == message.id
    assert received_message.sender == "pm"
    assert received_message.receiver == "irgat"


@pytest.mark.asyncio
async def test_handle_backpressure(message_bus: MessageBus):
    queue = ResizableQueue(maxsize=1)
    message_bus._queues["test_receiver"] = queue

    message1 = Message(id="1", sender="pm", receiver="test_receiver", msg_type="test", content={})
    message2 = Message(id="2", sender="pm", receiver="test_receiver", msg_type="test", content={})

    await queue.put(message1)
    await message_bus.send(message2)

    assert queue.qsize() == 1  # Message2 should wait until there's space

    received_message = await message_bus.receive("test_receiver")
    assert received_message.id == "1"

    received_message = await message_bus.receive("test_receiver")
    assert received_message.id == "2"


@pytest.mark.asyncio
async def test_adjust_queue_sizes(message_bus: MessageBus):
    queue = message_bus._queues["pm"]

    # Simulate a high load situation
    for i in range(int(queue.maxsize * 0.9)):
        await queue.put(Message(id=str(i), sender="test", receiver="pm", msg_type="test", content={}))

    await asyncio.sleep(61)  # Wait for the adjustment to be triggered

    assert queue.maxsize > Config.MAX_QUEUE_SIZE  # Should increase size


@pytest.mark.asyncio
async def test_resize_queue(message_bus: MessageBus):
    queue = ResizableQueue(maxsize=5)
    message_bus._queues["resize_test"] = queue

    # Fill the queue
    for i in range(5):
        await queue.put(Message(id=str(i), sender="test", receiver="resize_test", msg_type="test", content={}))

    # Resize
    queue.resize(10)
    assert queue.maxsize == 10

    # Check that new messages can be added
    new_message = Message(id="new", sender="test", receiver="resize_test", msg_type="test", content={})
    await queue.put(new_message)
    assert queue.qsize() == 6


@pytest.mark.asyncio
async def test_max_queue_size_edge_case(message_bus: MessageBus):
    max_queue_size = Config.MAX_QUEUE_SIZE
    queue = ResizableQueue(maxsize=max_queue_size)
    message_bus._queues["edge_case_receiver"] = queue

    # Fill the queue to its maximum size
    for i in range(max_queue_size):
        await queue.put(Message(id=str(i), sender="test", receiver="edge_case_receiver", msg_type="test", content={}))

    assert queue.qsize() == max_queue_size

    # Attempt to add one more message and check for backpressure handling
    message = Message(id="overflow", sender="test", receiver="edge_case_receiver", msg_type="test", content={})
    await message_bus.send(message)
    
    assert queue.qsize() == max_queue_size  # The queue should not exceed its max size


@pytest.mark.asyncio
async def test_message_loss_on_ack_timeout(message_bus: MessageBus):
    message = Message(id="lost_message", sender="pm", receiver="irgat", msg_type="test", content={})

    # Send a message but do not acknowledge it
    await message_bus.send(message)

    # Simulate a timeout without acknowledgment
    await asyncio.sleep(35)  # Longer than the default timeout

    # Check if the message was resent
    resent_message = await message_bus.receive("irgat")
    assert resent_message.id == message.id
