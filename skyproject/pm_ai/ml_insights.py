import pandas as pd
from sklearn.ensemble import RandomForestClassifier

class MLInsights:
    def __init__(self):
        self.model = RandomForestClassifier()
        # Assuming model training happens elsewhere, for simplicity

    def get_insights(self, tasks):
        features = self._extract_features(tasks)
        predictions = self.model.predict(features)
        return {task['id']: prediction for task, prediction in zip(tasks, predictions)}

    def _extract_features(self, tasks):
        # This function should convert task data into a feature matrix
        # For demonstration, assume tasks have 'feature1' and 'feature2'
        return pd.DataFrame([{ 'feature1': task['feature1'], 'feature2': task['feature2']} for task in tasks])
