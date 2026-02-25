from __future__ import annotations

import asyncio
import logging

from skyproject.core.task_store import TaskStore
from skyproject.core.communication import MessageBus
from skyproject.core.feedback_analysis import FeedbackAnalysis
from skyproject.core.ml_insights import MLInsights
from skyproject.core.improvement_tracker import ImprovementTracker
from skyproject.shared.models import TaskStatus, Message

logger = logging.getLogger(__name__)

class SelfImprovementFeedbackLoop:
    """
    Class to handle the self-improvement feedback loop mechanism.
    """

    def __init__(self, task_store: TaskStore, message_bus: MessageBus):
        self.task_store = task_store
        self.message_bus = message_bus
        self.improvement_tracker = ImprovementTracker(task_store)
        self._monitoring = False

    async def analyze_task_outcomes(self) -> dict[str, float]:
        """
        Analyze task outcomes to determine success and failure rates.
        :return: Dictionary containing success and failure rates.
        """
        return await self.improvement_tracker.calculate_proposal_effectiveness()

    async def review_and_propose_improvements(self) -> None:
        """
        Review and propose improvements based on feedback, failure analysis, ML insights, and sentiment analysis.
        """
        feedback_suggestions = FeedbackAnalysis.suggest_improvements(await self.analyze_task_outcomes())
        failure_analysis = FeedbackAnalysis.detailed_failure_analysis(await self.task_store.get_all())
        refined_suggestions = FeedbackAnalysis.refine_suggestions(failure_analysis)
        sentiment_results = FeedbackAnalysis.perform_sentiment_analysis(await self.task_store.get_all())
        sentiment_suggestions = FeedbackAnalysis.interpret_sentiment_results(sentiment_results)
        ml_insights = MLInsights.analyze_patterns(await self.task_store.get_all())

        suggestions = feedback_suggestions + refined_suggestions + sentiment_suggestions + ml_insights

        await self.message_bus.send(Message(id="improvement_proposal", sender="self_improvement", receiver="pm", msg_type="improvement_proposal", content={"suggestions": suggestions}))

    async def track_and_refine_improvement_proposals(self) -> None:
        """
        Track and refine improvement proposals based on their effectiveness.
        """
        refined_suggestions = await self.improvement_tracker.refine_proposals_based_on_performance()
        if refined_suggestions:
            await self.message_bus.send(Message(id="refined_proposal", sender="self_improvement", receiver="pm", msg_type="refined_proposal", content={"suggestions": refined_suggestions}))

    async def monitor_feedback(self) -> None:
        """
        Continuously monitor feedback and propose improvements.
        """
        self._monitoring = True
        while self._monitoring:
            try:
                await self.review_and_propose_improvements()
                await asyncio.sleep(60)  # Adjust as appropriate
            except Exception as e:
                logger.error("Error in feedback monitoring loop: %s", e)

    def stop_monitoring(self) -> None:
        """
        Stop the monitoring loop.
        """
        self._monitoring = False
