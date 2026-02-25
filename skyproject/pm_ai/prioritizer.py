def _adjust_weights(self) -> Tuple[float, float, float, float]:
    historical_trends = self.historical_data.mean()
    total_trend = historical_trends.sum()
    ml_insights = self.ml_insights.get_insights(self.historical_data.to_dict('records'))
    impact_weight = (historical_trends['impact'] + ml_insights.get('impact', 0)) / total_trend
    urgency_weight = (historical_trends['urgency'] + ml_insights.get('urgency', 0)) / total_trend
    stakeholder_weight = (historical_trends['stakeholder_priority'] + ml_insights.get('stakeholder_priority', 0)) / total_trend
    risk_weight = (historical_trends['risk'] + ml_insights.get('risk', 0)) / total_trend
    return impact_weight, urgency_weight, stakeholder_weight, risk_weight