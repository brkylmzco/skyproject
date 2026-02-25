import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from skyproject.core.self_improvement import SelfImprovementFeedbackLoop
from skyproject.core.task_store import TaskStore
from skyproject.core.communication import MessageBus
from skyproject.shared.models import TaskStatus, Message

@pytest.fixture
async def mock_task_store():
    store = MagicMock(TaskStore)
    store.count_by_status = AsyncMock(return_value={
        TaskStatus.COMPLETED.value: 8,
        TaskStatus.FAILED.value: 1,
        TaskStatus.CANCELLED.value: 1,
        TaskStatus.PENDING.value: 0,
        TaskStatus.IN_PROGRESS.value: 0
    })
    store.get_all = AsyncMock(return_value=[])
    store.get_completed = AsyncMock(return_value=[])
    return store

@pytest.fixture
async def mock_message_bus():
    bus = MagicMock(MessageBus)
    bus.send = AsyncMock()
    return bus

@pytest.fixture
async def feedback_loop(mock_task_store, mock_message_bus):
    return SelfImprovementFeedbackLoop(mock_task_store, mock_message_bus)

@pytest.mark.asyncio
async def test_analyze_task_outcomes(feedback_loop):
    results = await feedback_loop.analyze_task_outcomes()
    assert results["success_rate"] == 0.8
    assert results["failure_rate"] == 0.2

@pytest.mark.asyncio
async def test_review_and_propose_improvements(feedback_loop, mock_message_bus):
    feedback_loop._analyze_feedback = AsyncMock(return_value=["Feedback suggestion."])
    feedback_loop._analyze_failures = AsyncMock(return_value=["Failure suggestion."])
    feedback_loop._analyze_ml_patterns = AsyncMock(return_value=["ML insight."])
    feedback_loop._analyze_sentiments = AsyncMock(return_value=["Sentiment suggestion."])
    feedback_loop._detect_trends = AsyncMock(return_value=["Trend insight."])
    await feedback_loop.review_and_propose_improvements()
    mock_message_bus.send.assert_called_once()
    sent_message = mock_message_bus.send.call_args[0][0]
    assert sent_message.msg_type == "improvement_proposal"
    assert "Feedback suggestion." in sent_message.content["suggestions"]
    assert "Failure suggestion." in sent_message.content["suggestions"]
    assert "ML insight." in sent_message.content["suggestions"]
    assert "Sentiment suggestion." in sent_message.content["suggestions"]
    assert "Trend insight." in sent_message.content["suggestions"]

@pytest.mark.asyncio
async def test_monitor_feedback(feedback_loop):
    feedback_loop.review_and_propose_improvements = AsyncMock()

    monitoring_task = asyncio.create_task(feedback_loop.monitor_feedback())

    await asyncio.sleep(1)
    feedback_loop.stop_monitoring()

    await monitoring_task

    feedback_loop.review_and_propose_improvements.assert_called()

@pytest.mark.asyncio
async def test_monitor_feedback_exception_handling(feedback_loop):
    feedback_loop.review_and_propose_improvements = AsyncMock(side_effect=Exception("Test exception"))

    monitoring_task = asyncio.create_task(feedback_loop.monitor_feedback())

    await asyncio.sleep(1)
    feedback_loop.stop_monitoring()

    await monitoring_task

    feedback_loop.review_and_propose_improvements.assert_called()