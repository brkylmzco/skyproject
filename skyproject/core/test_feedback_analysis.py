import pytest
from skyproject.core.feedback_analysis import FeedbackAnalysis
from skyproject.shared.models import Task, TaskStatus


def test_analyze_feedback():
    tasks = [
        Task(id="1", title="Task 1", description="Desc 1", status=TaskStatus.COMPLETED),
        Task(id="2", title="Task 2", description="Desc 2", status=TaskStatus.FAILED, failure_reason="Error A"),
        Task(id="3", title="Task 3", description="Desc 3", status=TaskStatus.CANCELLED),
        Task(id="4", title="Task 4", description="Desc 4", status=TaskStatus.COMPLETED),
        Task(id="5", title="Task 5", description="Desc 5", status=TaskStatus.FAILED, failure_reason="Error B"),
        Task(id="6", title="Task 6", description="Desc 6", status=TaskStatus.FAILED, failure_reason="Error A"),
    ]

    analysis_results = FeedbackAnalysis.analyze_feedback(tasks)

    assert analysis_results['total_tasks'] == 6
    assert analysis_results['completed_tasks'] == 2
    assert analysis_results['failed_tasks'] == 3
    assert analysis_results['cancelled_tasks'] == 1


def test_suggest_improvements():
    analysis_results = {
        'total_tasks': 6,
        'completed_tasks': 2,
        'failed_tasks': 3,
        'cancelled_tasks': 1,
        'success_rate': 0.3333333333333333,
        'failure_rate': 0.6666666666666666,
    }

    suggestions = FeedbackAnalysis.suggest_improvements(analysis_results)

    assert "Review the common causes of task failures." in suggestions
    assert "Investigate reasons for task cancellations and improve task definitions." in suggestions


def test_detailed_failure_analysis():
    tasks = [
        Task(id="1", title="Task 1", description="Desc 1", status=TaskStatus.FAILED, failure_reason="Error A"),
        Task(id="2", title="Task 2", description="Desc 2", status=TaskStatus.FAILED, failure_reason="Error B"),
        Task(id="3", title="Task 3", description="Desc 3", status=TaskStatus.FAILED, failure_reason="Error A"),
    ]

    detailed_analysis = FeedbackAnalysis.detailed_failure_analysis(tasks)

    assert detailed_analysis['failure_reasons'] == [('Error A', 2), ('Error B', 1)]
    assert set(detailed_analysis['unique_failure_reasons']) == {'Error A', 'Error B'}


def test_refine_suggestions():
    detailed_analysis = {
        'failure_reasons': [('Error A', 2), ('Error B', 1)],
        'unique_failure_reasons': ['Error A', 'Error B']
    }

    refined_suggestions = FeedbackAnalysis.refine_suggestions(detailed_analysis)

    assert "Investigate Error A which occurred 2 times." in refined_suggestions
    assert "Investigate Error B which occurred 1 times." in refined_suggestions


def test_detect_trends():
    tasks = [
        Task(id="1", title="Task 1", description="Desc 1", status=TaskStatus.FAILED),
        Task(id="2", title="Task 2", description="Desc 2", status=TaskStatus.COMPLETED),
        Task(id="3", title="Task 3", description="Desc 3", status=TaskStatus.COMPLETED),
        Task(id="4", title="Task 4", description="Desc 4", status=TaskStatus.FAILED),
        Task(id="5", title="Task 5", description="Desc 5", status=TaskStatus.COMPLETED),
    ]

    trend_insights = FeedbackAnalysis.detect_trends(tasks)

    assert "Success rate is trending upwards." in trend_insights or "Success rate is trending downwards." in trend_insights or "Success rate is stable." in trend_insights
