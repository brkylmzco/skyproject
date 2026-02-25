import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from skyproject.pm_ai.prioritizer import TaskPrioritizer

@pytest.fixture
def historical_data_with_edge_cases():
    return pd.DataFrame({
        'feature1': [1, 2, 3, 0, 5],
        'feature2': [4, 5, 6, 7, 8],
        'impact': [7, 8, 9, 0, 12],
        'dependencies': [[], ['task1'], ['task2', 'task3'], [], []],
        'completion_time': [10, 20, 30, 0, 50],
        'resource_availability': [0.5, 0.9, 1.0, 0.1, 0.3],
        'urgency': [1, 2, 3, 0, 5],
        'stakeholder_priority': [1, 2, 3, 0, 5],
        'risk': [0.2, 0.4, 0.1, 0.0, 0.5],
        'roi': [0.5, 0.6, 0.7, 0.0, 0.8]
    })

@pytest.fixture
def tasks_with_various_attributes():
    return [
        {'feature1': 1, 'feature2': 4, 'dependencies': [], 'completion_time': 10, 'resource_availability': 0.5, 'urgency': 1, 'stakeholder_priority': 1, 'risk': 0.2, 'roi': 0.5},
        {'feature1': 2, 'feature2': 5, 'dependencies': ['task1'], 'completion_time': 20, 'resource_availability': 0.9, 'urgency': 2, 'stakeholder_priority': 2, 'risk': 0.4, 'roi': 0.6},
        {'feature1': 3, 'feature2': 6, 'dependencies': ['task2', 'task3'], 'completion_time': 30, 'resource_availability': 1.0, 'urgency': 3, 'stakeholder_priority': 3, 'risk': 0.1, 'roi': 0.7},
        {'feature1': 0, 'feature2': 7, 'dependencies': [], 'completion_time': 0, 'resource_availability': 0.1, 'urgency': 0, 'stakeholder_priority': 0, 'risk': 0.0, 'roi': 0.0},
        {'feature1': 5, 'feature2': 8, 'dependencies': [], 'completion_time': 50, 'resource_availability': 0.3, 'urgency': 5, 'stakeholder_priority': 5, 'risk': 0.5, 'roi': 0.8}
    ]

@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer.predict_impact')
def test_prioritize_tasks_with_edge_cases(mock_predict_impact, historical_data_with_edge_cases, tasks_with_various_attributes):
    mock_predict_impact.side_effect = [0.8, 0.6, 0.7, 0.3, 0.9]
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks(tasks_with_various_attributes)

    assert prioritized_tasks[0]['predicted_impact'] == 0.9
    assert prioritized_tasks[-1]['predicted_impact'] == 0.3

    for i in range(len(prioritized_tasks) - 1):
        assert prioritized_tasks[i]['priority_score'] >= prioritized_tasks[i + 1]['priority_score']

    assert prioritized_tasks[-1]['feature1'] == 0

    assert prioritized_tasks[0]['dependencies'] == []
    assert prioritized_tasks[-1]['dependencies'] == []

@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer._validate_data')
@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer.predict_impact', return_value=0.5)
def test_predict_impact_with_various_tasks(mock_predict_impact, mock_validate_data, historical_data_with_edge_cases, tasks_with_various_attributes):
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')

    for task in tasks_with_various_attributes:
        impact = prioritizer.predict_impact(task)
        assert impact == 0.5
        mock_predict_impact.assert_called_with(task)

@pytest.mark.parametrize('missing_feature_task', [
    {'feature1': 1, 'feature2': 4, 'completion_time': 10, 'resource_availability': 0.5, 'urgency': 1, 'stakeholder_priority': 1},
    {'feature1': 2, 'feature2': 5, 'completion_time': 20},
])
def test_prioritize_tasks_with_missing_features(historical_data_with_edge_cases, missing_feature_task):
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    with pytest.raises(ValueError, match='Missing required columns'):
        prioritizer.prioritize_tasks([missing_feature_task])

@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer._validate_data', side_effect=ValueError('Data contains null values'))
def test_prioritize_tasks_with_invalid_data(mock_validate_data, historical_data_with_edge_cases, tasks_with_various_attributes):
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')

    with pytest.raises(ValueError, match='Data contains null values'):
        prioritizer.prioritize_tasks(tasks_with_various_attributes)

@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer.predict_impact')
@pytest.mark.parametrize('task_data, expected_priority', [
    ({'feature1': 0, 'feature2': 7, 'dependencies': [], 'completion_time': 0, 'resource_availability': 0.1, 'urgency': 0, 'stakeholder_priority': 0, 'risk': 0.0, 'roi': 0.0}, 1),
    ({'feature1': 5, 'feature2': 8, 'dependencies': [], 'completion_time': 50, 'resource_availability': 0.3, 'urgency': 5, 'stakeholder_priority': 5, 'risk': 0.1, 'roi': 0.9}, 0),
    ({'feature1': 3, 'feature2': 6, 'dependencies': ['task2', 'task3'], 'completion_time': 30, 'resource_availability': 1.0, 'urgency': 3, 'stakeholder_priority': 3, 'risk': 0.1, 'roi': 0.7}, 2),
])
def test_prioritize_tasks_edge_case_scenarios(mock_predict_impact, task_data, expected_priority, historical_data_with_edge_cases):
    mock_predict_impact.return_value = task_data.get('predicted_impact', 0.5)
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks([task_data])
    assert prioritized_tasks[0]['priority_score'] == expected_priority


def test_prioritize_tasks_with_varied_urgency_and_priority(tasks_with_various_attributes, historical_data_with_edge_cases):
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks(tasks_with_various_attributes)
    assert prioritized_tasks[0]['urgency'] == 5
    assert prioritized_tasks[0]['stakeholder_priority'] == 5


def test_prioritize_tasks_with_no_dependencies(tasks_with_various_attributes, historical_data_with_edge_cases):
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    tasks_with_no_dependencies = [task for task in tasks_with_various_attributes if not task['dependencies']]
    prioritized_tasks = prioritizer.prioritize_tasks(tasks_with_no_dependencies)
    assert all(task['dependencies'] == [] for task in prioritized_tasks)


def test_prioritize_tasks_handles_large_input(tasks_with_various_attributes, historical_data_with_edge_cases):
    large_task_set = tasks_with_various_attributes * 100
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks(large_task_set)
    assert len(prioritized_tasks) == len(large_task_set)
    assert prioritized_tasks[0]['priority_score'] >= prioritized_tasks[-1]['priority_score']


def test_prioritize_tasks_with_high_risk(tasks_with_various_attributes, historical_data_with_edge_cases):
    tasks_with_high_risk = [{'feature1': 1, 'feature2': 4, 'dependencies': [], 'completion_time': 10, 'resource_availability': 0.5, 'urgency': 1, 'stakeholder_priority': 1, 'risk': 0.9, 'roi': 0.5}]
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks(tasks_with_high_risk)
    assert prioritized_tasks[0]['priority_score'] < 0


def test_prioritize_tasks_with_edge_urgency(tasks_with_various_attributes, historical_data_with_edge_cases):
    tasks_with_edge_urgency = [{'feature1': 1, 'feature2': 4, 'dependencies': [], 'completion_time': 10, 'resource_availability': 0.5, 'urgency': 10, 'stakeholder_priority': 1, 'risk': 0.2, 'roi': 0.5}]
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks(tasks_with_edge_urgency)
    assert prioritized_tasks[0]['priority_score'] > 0


def test_prioritize_tasks_with_missing_impact(historical_data_with_edge_cases):
    tasks_with_missing_impact = [{'feature1': 1, 'feature2': 4, 'dependencies': [], 'completion_time': 10, 'resource_availability': 0.5, 'urgency': 1, 'stakeholder_priority': 1, 'risk': 0.2, 'roi': 0.5}]
    prioritizer = TaskPrioritizer(historical_data_with_edge_cases, model_path='test_model.pkl')
    with pytest.raises(KeyError):
        prioritizer.prioritize_tasks(tasks_with_missing_impact)


def test_prioritize_tasks_with_faulty_data(tasks_with_various_attributes):
    faulty_historical_data = pd.DataFrame({
        'feature1': ['a', 'b', 'c'],
        'feature2': [4, 5, 6],
        'impact': [7, 8, 9],
        'dependencies': [[], ['task1'], ['task2', 'task3']],
        'completion_time': [10, 20, 30],
        'resource_availability': [0.5, 0.9, 1.0],
        'urgency': [1, 2, 3],
        'stakeholder_priority': [1, 2, 3],
        'risk': [0.2, 0.4, 0.1],
        'roi': [0.5, 0.6, 0.7]
    })
    prioritizer = TaskPrioritizer(faulty_historical_data, model_path='test_model.pkl')
    with pytest.raises(ValueError):
        prioritizer.prioritize_tasks(tasks_with_various_attributes)
