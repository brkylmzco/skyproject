import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.svm import OneClassSVM

class AnomalyDetector:
    def __init__(self, method='isolation_forest', **kwargs):
        self.method = method
        self.kwargs = kwargs
        self.detector = self._initialize_detector()

    def _initialize_detector(self):
        if self.method == 'isolation_forest':
            return IsolationForest(**self.kwargs)
        elif self.method == 'dbscan':
            return DBSCAN(**self.kwargs)
        elif self.method == 'one_class_svm':
            return OneClassSVM(**self.kwargs)
        else:
            raise ValueError(f'Unknown method: {self.method}')

    def fit(self, X):
        if not isinstance(X, np.ndarray):
            raise ValueError('Input data must be a numpy array')
        self.detector.fit(X)

    def predict(self, X):
        if not isinstance(X, np.ndarray):
            raise ValueError('Input data must be a numpy array')
        if self.method == 'isolation_forest' or self.method == 'one_class_svm':
            return self.detector.predict(X)
        elif self.method == 'dbscan':
            core_samples_mask = np.zeros_like(self.detector.labels_, dtype=bool)
            core_samples_mask[self.detector.core_sample_indices_] = True
            labels = self.detector.labels_
            return labels
        else:
            raise ValueError(f'Unknown method: {self.method}')

    def fit_predict(self, X):
        if not isinstance(X, np.ndarray):
            raise ValueError('Input data must be a numpy array')
        if self.method == 'isolation_forest' or self.method == 'one_class_svm':
            return self.detector.fit_predict(X)
        elif self.method == 'dbscan':
            self.detector.fit(X)
            return self.predict(X)
        else:
            raise ValueError(f'Unknown method: {self.method}')
