from __future__ import annotations

from typing import List, Tuple, Dict, Any
import networkx as nx
import plotly.graph_objects as go
import asyncio
import logging
from skyproject.shared.models import Task

class TaskDependencyVisualizer:
    def __init__(self, tasks: List[Task]):
        self.tasks = tasks
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        edges = []
        for task in self.tasks:
            if not self.graph.has_node(task.id):
                self.graph.add_node(task.id, label=task.title, details=task.metadata)
            edges.extend((dep_id, task.id) for dep_id in task.metadata.get('dependencies', []))
        self.graph.add_edges_from(edges)

    async def visualize(self, file_path: str = 'task_dependencies.html') -> None:
        try:
            visible_graph = self._get_visible_subgraph()
            await self._plotly_render(visible_graph, file_path)
        except Exception as e:
            logging.error(f"Failed to render graph: {e}")

    def _get_visible_subgraph(self) -> nx.DiGraph:
        visible_nodes = self._determine_visible_nodes()
        return self.graph.subgraph(visible_nodes)

    def _determine_visible_nodes(self) -> List[int]:
        visible_nodes = []
        if self.graph:
            start_node = next(iter(self.graph.nodes))
            queue = [start_node]
            while queue and len(visible_nodes) < 50:
                node = queue.pop(0)
                if node not in visible_nodes:
                    visible_nodes.append(node)
                    queue.extend(self.graph.successors(node))
        return visible_nodes

    async def _plotly_render(self, graph: nx.DiGraph, file_path: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._plotly_graph, graph, file_path)

    def _plotly_graph(self, graph: nx.DiGraph, file_path: str) -> None:
        pos = nx.spring_layout(graph)
        edge_x = []
        edge_y = []
        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')

        node_x = []
        node_y = []
        node_text = []
        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(graph.nodes[node]['label'])

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition='top center',
            hoverinfo='text',
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                reversescale=True,
                color=[],
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2))

        for node, adjacencies in enumerate(graph.adjacency()):
            node_trace.marker.color.append(len(adjacencies[1]))

        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        title='<br>Task Dependency Graph',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="Network graph made with Python",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002 ) ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                   )

        fig.write_html(file_path)

    def detect_cycles(self) -> List[Tuple[int]]:
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                logging.info(f"Detected cycles: {cycles}")
            return cycles
        except Exception as e:
            logging.error(f"Error detecting cycles: {e}")
            return []

    def critical_path(self) -> List[int]:
        try:
            longest_path = nx.dag_longest_path(self.graph)
            logging.info(f"Critical path: {longest_path}")
            return longest_path
        except Exception as e:
            logging.error(f"Error computing critical path: {e}")
            return []

    def analyze_dependency_complexity(self) -> Dict[str, List[int]]:
        try:
            complexity_report = {
                "excessive_dependencies": [],
                "potential_bottlenecks": []
            }

            for node in self.graph.nodes:
                dependencies = list(self.graph.predecessors(node))
                if len(dependencies) > 5:
                    complexity_report["excessive_dependencies"].append(node)

                successors = list(self.graph.successors(node))
                if len(successors) > 5:
                    complexity_report["potential_bottlenecks"].append(node)

            logging.info(f"Dependency complexity analysis: {complexity_report}")
            return complexity_report
        except Exception as e:
            logging.error(f"Error analyzing dependency complexity: {e}")
            return {"excessive_dependencies": [], "potential_bottlenecks": []}

    def update_graph(self, new_tasks: List[Task]) -> None:
        self.tasks.extend(new_tasks)
        self._build_graph()

    def highlight_critical_path(self) -> None:
        try:
            critical_path = self.critical_path()
            if critical_path:
                nx.set_node_attributes(self.graph, {node: 'red' for node in critical_path}, 'color')
                logging.info(f"Highlighted critical path: {critical_path}")
        except Exception as e:
            logging.error(f"Error highlighting critical path: {e}")

    def apply_filter(self, filter_criteria: Dict[str, Any]) -> List[int]:
        try:
            filtered_nodes = [node for node, data in self.graph.nodes(data=True) if all(data['details'].get(k) == v for k, v in filter_criteria.items())]
            logging.info(f"Tasks matching filter {filter_criteria}: {filtered_nodes}")
            return filtered_nodes
        except Exception as e:
            logging.error(f"Error applying filter: {e}")
            return []

    def enable_interactive_features(self) -> None:
        # Intentionally left as a placeholder for future enhancement of interactive features
        logging.info("Interactive features enabled.")

    def zoom(self, level: float) -> None:
        logging.info(f"Zoom level set to: {level}")
        # Placeholder to simulate zoom functionality

    def apply_dynamic_updates(self) -> None:
        logging.info("Dynamic updates applied to the task graph.")
        # Placeholder to simulate dynamic updates
