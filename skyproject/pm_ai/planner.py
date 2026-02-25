class Planner:
    def __init__(self):
        self.ml_insights = MLInsights()

    def plan_tasks(self, tasks):
        try:
            if not tasks:
                raise ValueError('No tasks to plan')
            logging.info('Planning %d tasks.', len(tasks))
            visualizer = TaskDependencyVisualizer(tasks)
            dependency_analysis = visualizer.analyze_dependency_complexity()
            logging.info('Dependency analysis: %s', dependency_analysis)

            # New clustering logic
            clustered_tasks = self._cluster_tasks(tasks)
            for cluster in clustered_tasks:
                insights = self.ml_insights.get_insights(cluster)
                logging.info('ML Insights for cluster: %s', insights)

                historical_data = self._prepare_historical_data(cluster)
                task_prioritizer = TaskPrioritizer(historical_data)
                prioritized_tasks = task_prioritizer.prioritize_tasks(cluster)

                for task in prioritized_tasks:
                    task_id = task.get('id', 'unknown')
                    task_insight = insights.get(task_id)
                    logging.info('Planning task %s with dependencies %s and insight %s', task_id, task.get('dependencies', []), task_insight)
                    if task_insight == 'high_priority':
                        task['urgency'] += 1
                    logging.info('Updated task %s', task)
        except ValueError as ve:
            task_ids = [task.get('id', 'unknown') for task in tasks]
            self._log_error(ErrorCode.PLANNER_VALIDATION_ERROR, 'Validation error while planning tasks', task_ids, ve, tasks)
            raise
        except Exception as e:
            task_ids = [task.get('id', 'unknown') for task in tasks]
            self._log_error(ErrorCode.PLANNER_ERROR, 'Error planning tasks', task_ids, e, tasks)
            raise

    def _cluster_tasks(self, tasks):
        # Basic clustering logic based on task features
        clusters = defaultdict(list)
        for task in tasks:
            key = (task.get('feature1'), task.get('feature2'))
            clusters[key].append(task)
        return clusters.values()

    def _prepare_historical_data(self, tasks):
        return pd.DataFrame([{k: task.get(k, 0) for k in ('feature1', 'feature2', 'impact', 'completion_time', 'resource_availability', 'urgency', 'stakeholder_priority')} for task in tasks])

    def _log_error(self, error_code, message, task_ids, error, tasks):
        logging.error(
            "%s - %s for tasks %s: %s | Tasks: %s",
            error_code.value,
            message,
            ', '.join(task_ids),
            str(error),
            str(tasks),
            exc_info=True
        )