from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(str, Enum):
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    SELF_IMPROVE = "self_improve"
    TEST = "test"
    DOCUMENTATION = "documentation"


class CodeChange(BaseModel):
    file_path: str
    old_content: Optional[str] = None
    new_content: str
    change_type: str = "create"  # create, modify, delete


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    target_module: str = ""  # pm_ai, irgat_ai, core, shared
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: str = "irgat"  # irgat or pm
    code_changes: list[CodeChange] = Field(default_factory=list)
    review_notes: str = ""
    parent_task_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    task_id: str
    approved: bool
    feedback: str
    quality_score: float = 0.0  # 0-10
    suggestions: list[str] = Field(default_factory=list)


class ImprovementProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str  # pm_ai or irgat_ai
    target: str  # which module to improve
    title: str
    description: str
    rationale: str
    estimated_impact: str = "medium"  # low, medium, high
    proposed_changes: list[CodeChange] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "proposed"  # proposed, approved, implemented, rejected

    def formatted_proposal(self) -> str:
        """Format the improvement proposal for clear presentation."""
        changes_formatted = "\n".join(
            [
                f"- {change.change_type.capitalize()} {change.file_path}:\n  {self._format_change_content(change)}"
                for change in self.proposed_changes
            ]
        )
        return (
            f"Proposal ID: {self.id}\n"
            f"Source: {self.source}\n"
            f"Target: {self.target}\n"
            f"Title: {self.title}\n"
            f"Description: {self.description}\n"
            f"Rationale: {self.rationale}\n"
            f"Estimated Impact: {self.estimated_impact}\n"
            f"Status: {self.status}\n"
            f"Proposed Changes:\n{changes_formatted}"
        )

    def _format_change_content(self, change: CodeChange) -> str:
        """Helper method to format the content of a code change."""
        old_content = change.old_content or "<none>"
        return f"Old: {old_content}\n  New: {change.new_content}"


class Message(BaseModel):
    """Communication message between PM AI and IrgatAI."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str  # pm or irgat
    receiver: str
    msg_type: str  # task_assign, status_update, review_request, review_result, improvement_proposal
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemState(BaseModel):
    """Overall system state for monitoring."""
    total_tasks_completed: int = 0
    total_improvements: int = 0
    pm_version: str = "0.1.0"
    irgat_version: str = "0.1.0"
    uptime_seconds: float = 0
    last_cycle_at: Optional[datetime] = None
    cycle_count: int = 0
