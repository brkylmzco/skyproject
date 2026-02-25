from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List

from skyproject.shared.models import Task, TaskStatus
from textblob import TextBlob
import numpy as np
from scipy.stats import linregress

logger = logging.getLogger(__name__)


class FeedbackAnalysis:
    """
    Analyze feedback from task executions and reviews to identify improvement patterns.
    """

    @staticmethod
    def analyze_feedback(tasks: List[Task]) -> Dict[str, Any]:
        """
        Analyze tasks to identify feedback patterns.
        :param tasks: List of Task objects
        :return: Dictionary with analysis results
        """
        status_counter = Counter(task.status for task in tasks)

        analysis_results = {
            'total_tasks': len(tasks),
            'completed_tasks': status_counter[TaskStatus.COMPLETED],
            'failed_tasks': status_counter[TaskStatus.FAILED],
            'cancelled_tasks': status_counter[TaskStatus.CANCELLED],
            'success_rate': status_counter[TaskStatus.COMPLETED] / len(tasks) if tasks else 0,
            'failure_rate': (status_counter[TaskStatus.FAILED] + status_counter[TaskStatus.CANCELLED]) / len(tasks) if tasks else 0
        }

        logger.info("Feedback Analysis: %s", analysis_results)

        return analysis_results

    @staticmethod
    def suggest_improvements(analysis_results: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements based on the analysis results.
        :param analysis_results: Results from feedback analysis
        :return: List of suggested improvements
        """
        suggestions = []

        if analysis_results['failed_tasks'] > 0:
            suggestions.append("Review the common causes of task failures.")

        if analysis_results['cancelled_tasks'] > 0:
            suggestions.append(
                "Investigate reasons for task cancellations and improve task definitions."
            )

        if analysis_results['success_rate'] < 0.9:
            suggestions.append(
                "Enhance task execution strategies to improve the success rate."
            )

        logger.info("Improvement Suggestions: %s", suggestions)

        return suggestions

    @staticmethod
    def detailed_failure_analysis(tasks: List[Task]) -> Dict[str, Any]:
        """
        Perform a detailed analysis of failed tasks to extract actionable insights.
        :param tasks: List of Task objects
        :return: Dictionary with detailed analysis of failures
        """
        failure_reasons = [task.failure_reason for task in tasks if task.status == TaskStatus.FAILED]
        failure_counter = Counter(failure_reasons)

        detailed_analysis = {
            'failure_reasons': failure_counter.most_common(),
            'unique_failure_reasons': list(failure_counter)
        }

        logger.info("Detailed Failure Analysis: %s", detailed_analysis)

        return detailed_analysis

    @staticmethod
    def refine_suggestions(detailed_analysis: Dict[str, Any]) -> List[str]:
        """
        Refine suggestions based on detailed failure analysis.
        :param detailed_analysis: Detailed analysis of failures
        :return: Refined suggestions
        """
        refined_suggestions = []

        if detailed_analysis['failure_reasons']:
            for reason, count in detailed_analysis['failure_reasons']:
                refined_suggestions.append(f"Investigate {reason} which occurred {count} times.")

        logger.info("Refined Suggestions: %s", refined_suggestions)

        return refined_suggestions

    @staticmethod
    def perform_sentiment_analysis(tasks: List[Task]) -> Dict[str, float]:
        """
        Perform sentiment analysis on task descriptions to gauge overall sentiment.
        :param tasks: List of Task objects
        :return: Dictionary with average polarity and subjectivity
        """
        polarities = []
        subjectivities = []

        for task in tasks:
            blob = TextBlob(task.description)
            polarities.append(blob.sentiment.polarity)
            subjectivities.append(blob.sentiment.subjectivity)

        average_polarity = sum(polarities) / len(polarities) if polarities else 0.0
        average_subjectivity = sum(subjectivities) / len(subjectivities) if subjectivities else 0.0

        sentiment_analysis_results = {
            'average_polarity': average_polarity,
            'average_subjectivity': average_subjectivity
        }

        logger.info("Sentiment Analysis Results: %s", sentiment_analysis_results)

        return sentiment_analysis_results

    @staticmethod
    def interpret_sentiment_results(sentiment_results: Dict[str, float]) -> List[str]:
        """
        Interpret sentiment analysis results into actionable suggestions.
        :param sentiment_results: Results from sentiment analysis
        :return: List of sentiment-based suggestions
        """
        suggestions = []

        if sentiment_results['average_polarity'] < -0.1:
            suggestions.append("Consider improving the sentiment of task descriptions.")
        elif sentiment_results['average_polarity'] < 0.1:
            suggestions.append("Neutral sentiment detected. Explore ways to enhance task engagement.")
        else:
            suggestions.append("Positive sentiment observed. Maintain this positive tone in future tasks.")

        if sentiment_results['average_subjectivity'] > 0.5:
            suggestions.append("High subjectivity detected. Ensure task descriptions are objective and clear.")

        logger.info("Sentiment Interpretation Suggestions: %s", suggestions)

        return suggestions

    @staticmethod
    def detect_trends(tasks: List[Task]) -> List[str]:
        """
        Detect trends in the success rate of tasks over time.
        :param tasks: List of Task objects
        :return: List of trend insights
        """
        insights = []
        try:
            if len(tasks) < 2:
                return insights

            # Assume tasks are sorted by time
            success_rates = [1 if task.status == TaskStatus.COMPLETED else 0 for task in tasks]
            x = np.arange(len(success_rates))
            slope, _, _, _, _ = linregress(x, success_rates)

            if slope > 0:
                insights.append("Success rate is trending upwards.")
            elif slope < 0:
                insights.append("Success rate is trending downwards.")
            else:
                insights.append("Success rate is stable.")
        except Exception as e:
            logger.error("Error detecting trends: %s", e)
        return insights
