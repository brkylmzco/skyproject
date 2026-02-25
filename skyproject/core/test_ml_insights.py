import pytest
from unittest.mock import patch, MagicMock
from skyproject.core.ml_insights import MLInsights
from skyproject.shared.models import Task

def test_analyze_patterns_empty_tasks():
    tasks = []
    insights = MLInsights.analyze_patterns(tasks)
    assert insights == []

def test_analyze_patterns_with_data():
    tasks = [
        Task(id="1", title="Task 1", description="Desc 1", status="completed", duration=MagicMock(total_seconds=MagicMock(return_value=3600)), complexity_level=3, resources_used=5),
        Task(id="2", title="Task 2", description="Desc 2", status="failed", duration=MagicMock(total_seconds=MagicMock(return_value=7200)), complexity_level=2, resources_used=3)
    ]

    with patch('skyproject.core.ml_insights.KMeans') as MockKMeans:
        mock_kmeans_instance = MockKMeans.return_value
        mock_kmeans_instance.labels_ = [0, 1]

        with patch('skyproject.core.ml_insights.PCA') as MockPCA:
            mock_pca_instance = MockPCA.return_value
            mock_pca_instance.explained_variance_ratio_ = [0.7, 0.2]

            with patch('skyproject.core.ml_insights.IsolationForest') as MockIsolationForest:
                mock_isolation_forest_instance = MockIsolationForest.return_value
                mock_isolation_forest_instance.fit_predict.return_value = [1, -1]

                insights = MLInsights.analyze_patterns(tasks)

                assert len(insights) == 4  # We expect four insights: two clusters, PCA explanation, and anomaly detection
                assert "Cluster" in insights[0]
                assert "PCA explained variance" in insights[2]
                assert "Detected 1 anomalies" in insights[3]

def test_prepare_data_with_invalid_data():
    tasks = [
        Task(id="1", title="Task 1", description="Desc 1", status="completed", duration=None)
    ]
    data = MLInsights._prepare_data(tasks)
    assert data == []
