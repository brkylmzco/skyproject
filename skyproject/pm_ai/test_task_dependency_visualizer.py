import pytest
from skyproject.pm_ai.task_dependency_visualizer import TaskDependencyVisualizer
from skyproject.shared.models import Task

@pytest.mark.asyncio
def test_detect_cycles():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': [3]}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
        Task(id=3, title='Task 3', metadata={'dependencies': [2]}),  # Cycle: 1 -> 3 -> 2 -> 1
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    cycles = visualizer.detect_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {1, 2, 3}

@pytest.mark.asyncio
def test_critical_path():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': []}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
        Task(id=3, title='Task 3', metadata={'dependencies': [1]}),
        Task(id=4, title='Task 4', metadata={'dependencies': [2, 3]}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    critical_path = visualizer.critical_path()
    assert critical_path == [1, 2, 4] or critical_path == [1, 3, 4], "Critical path should be one of the longest paths"

@pytest.mark.asyncio
def test_visualize_large_graph():
    tasks = [
        Task(id=i, title=f'Task {i}', metadata={'dependencies': [i - 1]}) for i in range(1, 100)
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    try:
        await visualizer.visualize(file_path='large_task_dependencies.html')
    except Exception as e:
        pytest.fail(f"Visualization of large graph failed: {e}")

@pytest.mark.asyncio
def test_no_cycles():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': [2]}),
        Task(id=2, title='Task 2', metadata={'dependencies': [3]}),
        Task(id=3, title='Task 3', metadata={'dependencies': []}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    cycles = visualizer.detect_cycles()
    assert cycles == [], "Should detect no cycles"

@pytest.mark.asyncio
def test_multiple_disconnected_graphs():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': []}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
        Task(id=3, title='Task 3', metadata={'dependencies': []}),
        Task(id=4, title='Task 4', metadata={'dependencies': [3]}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    critical_path = visualizer.critical_path()
    assert critical_path in ([1, 2], [3, 4]), "Critical path should be one of the longest paths in the graph"

@pytest.mark.asyncio
def test_large_cyclic_graph_detection():
    tasks = [
        Task(id=i, title=f'Task {i}', metadata={'dependencies': [i + 1]}) for i in range(1, 100)
    ]
    tasks.append(Task(id=100, title='Task 100', metadata={'dependencies': [1]}))  # Adding a cycle
    visualizer = TaskDependencyVisualizer(tasks)
    cycles = visualizer.detect_cycles()
    assert len(cycles) == 1, "Should detect one cycle in the graph"
    assert set(cycles[0]) == set(range(1, 101)), "Cycle should include all tasks"

@pytest.mark.asyncio
def test_hover_highlight():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': []}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)

    # Check if hovering over a node would highlight it (interaction test)
    # This would normally be a UI test, but we can simulate hover events
    # by testing if the function exists and doesn't raise errors
    try:
        visualizer._plotly_graph(visualizer.graph, 'test_hover.html')  # We mock the graph interactions
    except Exception as e:
        pytest.fail(f"Interactivity failed: {e}")

@pytest.mark.asyncio
def test_empty_task_list():
    """Test handling of an empty task list."""
    visualizer = TaskDependencyVisualizer([])
    assert visualizer.detect_cycles() == [], "No cycles should be found in an empty graph"
    assert visualizer.critical_path() == [], "Critical path should be empty for an empty graph"

@pytest.mark.asyncio
def test_single_task_no_dependencies():
    """Test a single task with no dependencies."""
    task = Task(id=1, title='Task 1', metadata={'dependencies': []})
    visualizer = TaskDependencyVisualizer([task])
    assert visualizer.detect_cycles() == [], "No cycles should be found with a single task"
    assert visualizer.critical_path() == [1], "The single task should be the critical path"

@pytest.mark.asyncio
def test_task_with_self_dependency():
    """Test a task with a self-dependency (cycle)."""
    task = Task(id=1, title='Task 1', metadata={'dependencies': [1]})
    visualizer = TaskDependencyVisualizer([task])
    cycles = visualizer.detect_cycles()
    assert len(cycles) == 1, "Should detect one cycle involving the task itself"
    assert cycles[0] == [1], "The cycle should consist of the single task"

@pytest.mark.asyncio
def test_analyze_dependency_complexity():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': [2, 3, 4, 5, 6, 7]}),  # Excessive dependencies
        Task(id=2, title='Task 2', metadata={'dependencies': []}),
        Task(id=3, title='Task 3', metadata={'dependencies': []}),
        Task(id=4, title='Task 4', metadata={'dependencies': []}),
        Task(id=5, title='Task 5', metadata={'dependencies': []}),
        Task(id=6, title='Task 6', metadata={'dependencies': []}),
        Task(id=7, title='Task 7', metadata={'dependencies': []}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    complexity_report = visualizer.analyze_dependency_complexity()
    assert complexity_report['excessive_dependencies'] == [1], "Task 1 should have excessive dependencies"
    assert complexity_report['potential_bottlenecks'] == [], "No bottlenecks should be detected"

@pytest.mark.asyncio
def test_dynamic_update():
    """Test dynamic update of the graph when new tasks are added."""
    initial_tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': []}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
    ]
    visualizer = TaskDependencyVisualizer(initial_tasks)
    new_tasks = [
        Task(id=3, title='Task 3', metadata={'dependencies': [2]}),
        Task(id=4, title='Task 4', metadata={'dependencies': [3]}),
    ]
    visualizer.update_graph(new_tasks)
    critical_path = visualizer.critical_path()
    assert critical_path == [1, 2, 3, 4], "Critical path should include newly added tasks"

@pytest.mark.asyncio
def test_highlight_critical_path():
    """Test highlighting of the critical path."""
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': []}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
        Task(id=3, title='Task 3', metadata={'dependencies': [2]}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    visualizer.highlight_critical_path()
    for node in visualizer.critical_path():
        assert visualizer.graph.nodes[node].get('color') == 'red', "Critical path nodes should be highlighted red"

@pytest.mark.asyncio
def test_apply_filter():
    tasks = [
        Task(id=1, title='Task 1', metadata={'dependencies': []}),
        Task(id=2, title='Task 2', metadata={'dependencies': [1]}),
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    filter_criteria = {'dependencies': [1]}
    filtered_nodes = visualizer.apply_filter(filter_criteria)
    assert filtered_nodes == [2], "Filtering should return task with dependency on 1"

@pytest.mark.asyncio
def test_lazy_loading_large_graph():
    """Test that lazy loading works for large graphs."""
    tasks = [
        Task(id=i, title=f'Task {i}', metadata={'dependencies': [i - 1]}) for i in range(1, 500)
    ]
    visualizer = TaskDependencyVisualizer(tasks)
    visible_subgraph = visualizer._get_visible_subgraph()
    assert len(visible_subgraph.nodes) <= 50, "Only a subset of nodes should be loaded initially for large graphs"
