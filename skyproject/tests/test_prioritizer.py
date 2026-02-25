import unittest
import pandas as pd
from skyproject.pm_ai.prioritizer import TaskPrioritizer


class TestTaskPrioritizer(unittest.TestCase):
    def setUp(self):
        self.historical_data = pd.DataFrame({
            'feature1': [1, 2, 3, 4],
            'feature2': [2, 3, 4, 5],
            'impact': [5, 6, 7, 8]
        })
        self.prioritizer = TaskPrioritizer(self.historical_data)

    def test_predict_impact(self):
        task_features = {'feature1': 5, 'feature2': 6}
        predicted_impact = self.prioritizer.predict_impact(task_features)
        self.assertIsInstance(predicted_impact, float)

    def test_prioritize_tasks(self):
        tasks = [
            {'feature1': 5, 'feature2': 6},
            {'feature1': 3, 'feature2': 4},
            {'feature1': 1, 'feature2': 2}
        ]
        prioritized_tasks = self.prioritizer.prioritize_tasks(tasks)
        self.assertEqual(len(prioritized_tasks), 3)
        self.assertGreaterEqual(prioritized_tasks[0]['predicted_impact'], prioritized_tasks[1]['predicted_impact'])

    def test_missing_impact_column(self):
        with self.assertRaises(ValueError):
            TaskPrioritizer(pd.DataFrame({'feature1': [1, 2], 'feature2': [3, 4]}))

    def test_missing_values(self):
        with self.assertRaises(ValueError):
            TaskPrioritizer(pd.DataFrame({'feature1': [1, None], 'feature2': [3, 4], 'impact': [5, 6]}))


if __name__ == '__main__':
    unittest.main()
