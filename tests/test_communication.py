import pytest
import asyncio
from skyproject.core.communication import MessageBus
from skyproject.shared.models import Message

@pytest.fixture
def message_bus() -> MessageBus:
    return MessageBus()

@pytest.fixture
def sample_message() -> Message:
    return Message(
        sender="pm",
        receiver="irgat",
        msg_type="task_assign",
        payload={"task_id": "123", "description": "Test task"}
    )

@pytest.mark.asyncio
async def test_send_and_receive_message(message_bus: MessageBus, sample_message: Message):
    await message_bus.send(sample_message)
    received_message = await message_bus.receive("irgat")
    assert received_message is not None
    assert received_message.id == sample_message.id

@pytest.mark.asyncio
async def test_receive_timeout(message_bus: MessageBus):
    received_message = await message_bus.receive("irgat", timeout=1.0)
    assert received_message is None

@pytest.mark.asyncio
async def test_subscribe_and_handler_execution(message_bus: MessageBus, sample_message: Message):
    handler_executed = False

    async def handler(message: Message):
        nonlocal handler_executed
        handler_executed = True

    message_bus.subscribe("task_assign", handler)
    await message_bus.send(sample_message)
    await asyncio.sleep(0.1)  # Give the handler time to execute
    assert handler_executed

@pytest.mark.asyncio
async def test_receive_all_messages(message_bus: MessageBus, sample_message: Message):
    await message_bus.send(sample_message)
    await message_bus.send(sample_message)
    messages = await message_bus.receive_all("irgat")
    assert len(messages) == 2

@pytest.mark.asyncio
async def test_message_history(message_bus: MessageBus, sample_message: Message):
    await message_bus.send(sample_message)
    history = message_bus.get_history()
    assert len(history) == 1
    assert history[0].id == sample_message.id