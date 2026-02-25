from __future__ import annotations

import logging
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from typing import List
import numpy as np

from skyproject.shared.models import Task

logger = logging.getLogger(__name__)


class MLInsights:
    """
    A module to generate machine learning insights from task data, including anomaly detection and trend analysis.
    """

    @staticmethod
    def analyze_patterns(tasks: List[Task]) -> List[str]:
        """
        Analyze task performance patterns using machine learning techniques.
        :param tasks: List of Task objects
        :return: List of insights as strings
        """
        try:
            data = MLInsights._prepare_data(tasks)
            if not data:
                logger.warning("No data available for analysis.")
                return []

            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data)

            # Apply PCA for dimensionality reduction
            pca = PCA(n_components=2)  # Reduce to two dimensions for visualization
            reduced_data = pca.fit_transform(scaled_data)

            # Using 3 clusters as a default for simplicity and initial pattern discovery.
            kmeans = KMeans(n_clusters=3, random_state=42)
            kmeans.fit(reduced_data)
            labels = kmeans.labels_

            insights = MLInsights._generate_insights(labels, pca.explained_variance_ratio_)
            
            # Detect anomalies
            anomalies = MLInsights._detect_anomalies(scaled_data)
            insights.extend(anomalies)

            # Analyze trends
            trends = MLInsights._analyze_trends(scaled_data)
            insights.extend(trends)

            return insights
        except Exception as e:
            logger.error("Error during ML insights analysis: %s", e)
            return []

    @staticmethod
    def _prepare_data(tasks: List[Task]) -> List[List[float]]:
        """
        Prepare the task data for machine learning analysis.
        :param tasks: List of Task objects
        :return: List of feature lists
        """
        try:
            return [
                [
                    task.duration.total_seconds(),
                    task.complexity_level,
                    task.resources_used
                ]
                for task in tasks if task.duration is not None
            ]
        except AttributeError as e:
            logger.error("Data preparation error: %s", e)
            return []

    @staticmethod
    def _generate_insights(labels: List[int], variance_ratios: List[float]) -> List[str]:
        """
        Generate human-readable insights from clustering labels and PCA variance ratios.
        :param labels: List of clustering labels
        :param variance_ratios: Variance ratios from PCA
        :return: List of insights
        """
        insights = []
        try:
            cluster_counts = Counter(labels)
            for cluster_id, count in cluster_counts.items():
                insights.append(f"Cluster {cluster_id} contains {count} tasks.")

            total_variance_explained = sum(variance_ratios) * 100
            insights.append(f"PCA explained variance: {total_variance_explained:.2f}%.")
        except Exception as e:
            logger.error("Error generating insights: %s", e)
        return insights

    @staticmethod
    def _detect_anomalies(data: List[List[float]]) -> List[str]:
        """
        Detect anomalies in task data using Isolation Forest.
        :param data: List of feature lists
        :return: List of anomaly insights
        """
        insights = []
        try:
            isolation_forest = IsolationForest(contamination=0.1, random_state=42)
            predictions = isolation_forest.fit_predict(data)

            anomaly_count = sum(1 for p in predictions if p == -1)
            if anomaly_count:
                insights.append(f"Detected {anomaly_count} anomalies in task data.")
        except Exception as e:
            logger.error("Error detecting anomalies: %s", e)
        return insights

    @staticmethod
    def _analyze_trends(data: List[List[float]]) -> List[str]:
        """
        Analyze trends in task data using linear regression.
        :param data: List of feature lists
        :return: List of trend insights
        """
        insights = []
        try:
            if len(data) >= 2:  # Need at least two points for trend analysis
                x = np.arange(len(data)).reshape(-1, 1)  # Use index as the independent variable
                y = np.array(data)

                for i, feature in enumerate(['Duration', 'Complexity', 'Resources']):
                    model = LinearRegression()
                    model.fit(x, y[:, i])
                    slope = model.coef_[0]
                    insights.append(f"Trend for {feature}: {'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable' }.")
        except Exception as e:
            logger.error("Error analyzing trends: %s", e)
        return insights
