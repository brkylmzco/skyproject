import pytest
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from unittest.mock import patch, MagicMock
from sklearn.preprocessing import StandardScaler
from skyproject.pm_ai.prioritizer import TaskPrioritizer


@pytest.fixture
def sample_historical_data():
    return pd.DataFrame({
        'feature1': [1, 2, 3],
        'feature2': [4, 5, 6],
        'impact': [7, 8, 9],
        'dependencies': [[0], [1], [2]],
        'completion_time': [10, 20, 30],
        'resource_availability': [0.8, 0.9, 1.0],
        'urgency': [1, 2, 3],
        'stakeholder_priority': [1, 2, 3]
    })


@pytest.fixture
def sample_tasks():
    return [
        {'feature1': 1, 'feature2': 4, 'dependencies': [0], 'completion_time': 10, 'resource_availability': 0.8, 'urgency': 1, 'stakeholder_priority': 1},
        {'feature1': 2, 'feature2': 5, 'dependencies': [1], 'completion_time': 20, 'resource_availability': 0.9, 'urgency': 2, 'stakeholder_priority': 2},
        {'feature1': 3, 'feature2': 6, 'dependencies': [2], 'completion_time': 30, 'resource_availability': 1.0, 'urgency': 3, 'stakeholder_priority': 3}
    ]


@pytest.fixture
def mock_model():
    mock = MagicMock(spec=GradientBoostingRegressor)
    mock.predict.return_value = [0.5, 0.75, 0.6]
    return mock


@patch('joblib.dump')
@patch('joblib.load')
def test_load_existing_model(mock_load, mock_dump, sample_historical_data):
    mock_load.return_value = GradientBoostingRegressor()
    prioritizer = TaskPrioritizer(sample_historical_data, model_path='existing_model.pkl')
    mock_load.assert_called_once_with('existing_model.pkl')
    assert isinstance(prioritizer.model, GradientBoostingRegressor)


@patch('skyproject.pm_ai.prioritizer.TaskPrioritizer._train_model')
def test_train_new_model(mock_train_model, sample_historical_data):
    mock_train_model.return_value = GradientBoostingRegressor()
    prioritizer = TaskPrioritizer(sample_historical_data, model_path='non_existent_model.pkl')
    mock_train_model.assert_called_once()
    assert isinstance(prioritizer.model, GradientBoostingRegressor)


@patch.object(TaskPrioritizer, '_validate_data')
def test_validate_data_called_during_training(mock_validate_data, sample_historical_data):
    TaskPrioritizer(sample_historical_data)
    mock_validate_data.assert_called_once_with(sample_historical_data)


@patch.object(TaskPrioritizer, '_validate_data')
@patch('joblib.load')
def test_predict_impact(mock_load, mock_validate_data, sample_historical_data, mock_model):
    mock_load.return_value = mock_model
    prioritizer = TaskPrioritizer(sample_historical_data)
    task_features = {'feature1': 2, 'feature2': 5, 'dependencies': [1], 'completion_time': 20, 'resource_availability': 0.9, 'urgency': 2, 'stakeholder_priority': 2}
    impact = prioritizer.predict_impact(task_features)
    mock_validate_data.assert_called_with(pd.DataFrame([task_features]))
    assert impact == 0.75


@patch('joblib.load')
@patch('joblib.dump')
def test_prioritize_tasks(mock_dump, mock_load, sample_historical_data, sample_tasks, mock_model):
    mock_load.return_value = mock_model
    prioritizer = TaskPrioritizer(sample_historical_data, model_path='model_with_scaler.pkl')
    prioritized_tasks = prioritizer.prioritize_tasks(sample_tasks)
    assert prioritized_tasks[0]['predicted_impact'] == 0.75  # Highest impact task
    assert prioritized_tasks[1]['predicted_impact'] == 0.6
    assert prioritized_tasks[2]['predicted_impact'] == 0.5


@pytest.mark.parametrize('invalid_data', [
    pd.DataFrame({'feature1': [1], 'impact': [None]}),  # Missing impact
    pd.DataFrame({'feature1': [1]})  # No impact column
])
def test_validate_data_raises_error_for_invalid_data(invalid_data):
    with pytest.raises(ValueError):
        TaskPrioritizer._validate_data(invalid_data)


def test_scaler_persistence(sample_historical_data):
    prioritizer = TaskPrioritizer(sample_historical_data, model_path='test_model.pkl')
    assert isinstance(prioritizer.scaler, StandardScaler)
    dump(prioritizer.scaler, 'test_scaler.pkl')
    loaded_scaler = load('test_scaler.pkl')
    assert isinstance(loaded_scaler, StandardScaler)


def test_empty_historical_data_raises_error():
    with pytest.raises(ValueError, match='Historical data is required for initialization'):
        TaskPrioritizer(pd.DataFrame(), model_path='test_model.pkl')


def test_prioritize_tasks_with_empty_list():
    prioritizer = TaskPrioritizer(pd.DataFrame({
        'feature1': [1],
        'feature2': [2],
        'impact': [3],
        'dependencies': [[0]],
        'completion_time': [4],
        'resource_availability': [0.5],
        'urgency': [1],
        'stakeholder_priority': [1]
    }), model_path='test_model.pkl')
    with pytest.raises(ValueError, match='No tasks provided for prioritization'):
        prioritizer.prioritize_tasks([])


def test_prioritize_tasks_handles_large_number_of_tasks(sample_historical_data):
    mock_model = MagicMock(spec=GradientBoostingRegressor)
    mock_model.predict.return_value = [i * 0.01 for i in range(1000)]
    tasks = [{'feature1': i, 'feature2': i + 1, 'dependencies': [i], 'completion_time': i + 2, 'resource_availability': 0.5, 'urgency': i % 5, 'stakeholder_priority': i % 5} for i in range(1000)]
    with patch('joblib.load', return_value=mock_model):
        prioritizer = TaskPrioritizer(sample_historical_data, model_path='model_with_scaler.pkl')
        prioritized_tasks = prioritizer.prioritize_tasks(tasks)
        assert len(prioritized_tasks) == 1000
        assert prioritized_tasks[0]['predicted_impact'] == 9.99  # Highest impact task
        assert prioritized_tasks[-1]['predicted_impact'] == 0.0  # Lowest impact task


def test_retry_fallback():
    prioritizer = TaskPrioritizer(pd.DataFrame({
        'feature1': [1],
        'feature2': [2],
        'impact': [3],
        'dependencies': [[0]],
        'completion_time': [4],
        'resource_availability': [0.5],
        'urgency': [1],
        'stakeholder_priority': [1]
    }), model_path='test_model.pkl')

    def always_fail():
        raise ValueError('Simulated error')

    with pytest.raises(ValueError, match='Simulated error'):
        prioritizer._retry_fallback(always_fail, retries=2)

    try_count = 0
    def fail_twice():
        nonlocal try_count
        if try_count < 2:
            try_count += 1
            raise ValueError('Simulated error')
        return 'Success'

    assert prioritizer._retry_fallback(fail_twice, retries=3) == 'Success'


def test_feature_enhancement(sample_historical_data):
    prioritizer = TaskPrioritizer(sample_historical_data)
    assert 'num_dependencies' in prioritizer.historical_data.columns
    assert 'average_dependency_urgency' in prioritizer.historical_data.columns
