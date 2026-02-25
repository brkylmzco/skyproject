import pytest
import asyncio
from unittest.mock import patch, MagicMock
from skyproject.irgat_ai.coder import Coder
from skyproject.shared.models import Task, CodeChange

@pytest.mark.asyncio
async def test_implement_generates_code_changes():
    llm_mock = MagicMock()
    llm_mock.generate_json = MagicMock(return_value={
        'changes': [
            {
                'file_path': 'skyproject/irgat_ai/some_file.py',
                'new_content': 'def new_function(): pass',
                'change_type': 'create'
            }
        ]
    })
    coder = Coder(llm_mock)
    task = Task(title='New Feature', description='Implement new feature', target_module='irgat_ai', task_type='feature')
    changes = await coder.implement(task)

    assert len(changes) == 1
    assert changes[0].file_path == 'skyproject/irgat_ai/some_file.py'
    assert changes[0].new_content == 'def new_function(): pass'
    assert changes[0].change_type == 'create'

@pytest.mark.asyncio
async def test_improve_from_feedback_generates_correct_changes():
    llm_mock = MagicMock()
    llm_mock.generate_json = MagicMock(return_value={
        'changes': [
            {
                'file_path': 'skyproject/irgat_ai/some_file.py',
                'new_content': 'def improved_function(): pass',
                'change_type': 'modify'
            }
        ]
    })
    coder = Coder(llm_mock)
    task = Task(title='Improve Feature', description='Improve existing feature', target_module='irgat_ai', task_type='improvement')
    feedback = 'Function implementation is incorrect.'
    suggestions = ['Use correct logic.']
    changes = await coder.improve_from_feedback(task, feedback, suggestions)

    assert len(changes) == 1
    assert changes[0].file_path == 'skyproject/irgat_ai/some_file.py'
    assert changes[0].new_content == 'def improved_function(): pass'
    assert changes[0].change_type == 'modify'
