import pytest
from skyproject.pm_ai.reviewer import Reviewer
from skyproject.shared.models import Task


@pytest.mark.asyncio
def test_format_changes():
    reviewer = Reviewer()

    changes = [
        {
            'file_path': 'example.py',
            'change_type': 'modify',
            'old_content': 'print("Hello")',
            'new_content': 'print("Hello, World!")'
        },
        {
            # Deliberately incomplete change dict to test error handling
            'file_path': 'example2.py'
        }
    ]

    formatted_changes = list(reviewer._format_changes(changes))

    assert len(formatted_changes) == 2
    assert 'File: example.py' in formatted_changes[0]
    assert 'File: example2.py' in formatted_changes[1]
    assert 'Type: Modify' in formatted_changes[0]
    assert 'Type: Modify' in formatted_changes[1]  # Default value
    assert 'Old Content: <none>' in formatted_changes[1]  # Default value
    assert 'New Content: <none>' in formatted_changes[1]  # Default value
