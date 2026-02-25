import pytest
from skyproject.irgat_ai.tester import Tester
from skyproject.shared.models import CodeChange

@pytest.mark.asyncio
def test_validate_changes_valid_syntax():
    tester = Tester()
    changes = [CodeChange(file_path='example.py', new_content='import os\nprint("Hello")', change_type='modify')]
    result = await tester.validate_changes(changes)
    assert result is True

@pytest.mark.asyncio
def test_validate_changes_syntax_error():
    tester = Tester()
    changes = [CodeChange(file_path='example.py', new_content='import os\nprint("Hello"', change_type='modify')]
    result = await tester.validate_changes(changes)
    assert result is False

@pytest.mark.asyncio
def test_validate_changes_import_error():
    tester = Tester()
    changes = [CodeChange(file_path='example.py', new_content='import non_existent_module\nprint("Hello")', change_type='modify')]
    result = await tester.validate_changes(changes)
    assert result is False
