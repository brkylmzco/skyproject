def _adjust_weights(self) -> Tuple[float, float, float, float]:
    historical_trends = self.historical_data.mean()
    total_trend = historical_trends.sum()
    impact_weight = (historical_trends['impact'] / total_trend)
    urgency_weight = (historical_trends['urgency'] / total_trend)
    stakeholder_weight = (historical_trends['stakeholder_priority'] / total_trend)
    risk_weight = (historical_trends['risk'] / total_trend)
    return impact_weight, urgency_weight, stakeholder_weight, risk_weight

    def prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        impact_weight, urgency_weight, stakeholder_weight, risk_weight = self._adjust_weights()
        for task in tasks:
            task['priority_score'] = (task['predicted_impact'] * impact_weight +
                                      task['urgency'] * urgency_weight +
                                      task['stakeholder_priority'] * stakeholder_weight -
                                      task['risk'] * risk_weight)
        return sorted(tasks, key=lambda x: x['priority_score'], reverse=True)