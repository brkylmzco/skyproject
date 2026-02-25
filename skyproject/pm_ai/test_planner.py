import pytest
from unittest.mock import patch, MagicMock
from skyproject.pm_ai.planner import Planner


@pytest.fixture
def sample_tasks():
    return [
        {'id': 'task1', 'feature1': 1, 'feature2': 4, 'dependencies': [], 'urgency': 1, 'completion_time': 10, 'resource_availability': 0.8, 'stakeholder_priority': 1},
        {'id': 'task2', 'feature1': 2, 'feature2': 5, 'dependencies': ['task1'], 'urgency': 2, 'completion_time': 20, 'resource_availability': 0.9, 'stakeholder_priority': 2}
    ]


@patch('skyproject.pm_ai.ml_insights.MLInsights.get_insights', return_value={'task1': 'high_priority', 'task2': 'normal'})
@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer.prioritize_tasks', side_effect=lambda tasks: tasks)
def test_plan_tasks_with_insights(mock_prioritize_tasks, mock_get_insights, sample_tasks):
    planner = Planner()
    planner.plan_tasks(sample_tasks)
    assert sample_tasks[0]['urgency'] == 2  # Urgency increased due to high priority insight
    assert sample_tasks[1]['urgency'] == 2  # Urgency unchanged
    mock_prioritize_tasks.assert_called_once()
    mock_get_insights.assert_called_once()
