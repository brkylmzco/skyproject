from __future__ import annotations

import logging
from typing import List, Dict

from skyproject.core.task_store import TaskStore
from skyproject.shared.models import Task, TaskStatus


logger = logging.getLogger(__name__)


class ImprovementTracker:
    """
    Class responsible for tracking and analyzing self-improvement proposals.
    """

    def __init__(self, task_store: TaskStore):
        self.task_store = task_store

    async def calculate_proposal_effectiveness(self) -> Dict[str, float]:
        """
        Calculate the effectiveness of self-improvement proposals based on task success and failure rates.
        :return: Dictionary containing success and failure rates.
        """
        tasks = await self.task_store.get_all()
        if not tasks:
            logger.info("No tasks available for analysis.")
            return {"success_rate": 0.0, "failure_rate": 0.0}

        success_count = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
        failure_count = sum(1 for task in tasks if task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED])

        total = len(tasks)
        success_rate = success_count / total if total > 0 else 0.0
        failure_rate = failure_count / total if total > 0 else 0.0

        logger.info("Calculated proposal effectiveness: Success rate: %.2f%%, Failure rate: %.2f%%", success_rate * 100, failure_rate * 100)

        return {
            "success_rate": success_rate,
            "failure_rate": failure_rate
        }

    async def refine_proposals_based_on_performance(self) -> List[str]:
        """
        Refine proposals based on performance data.
        :return: List of refined suggestions.
        """
        effectiveness = await self.calculate_proposal_effectiveness()
        suggestions = []

        if effectiveness["failure_rate"] > 0.1:
            suggestions.append("Investigate and address causes of high failure rates.")

        if effectiveness["success_rate"] < 0.9:
            suggestions.append("Enhance strategies to improve task completion rates.")

        logger.info("Refined proposals based on performance: %s", suggestions)

        return suggestions
