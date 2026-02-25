import pytest
from unittest.mock import AsyncMock
from skyproject.pm_ai.self_improve import PMSelfImprover
from skyproject.shared.llm_client import LLMClient

@pytest.fixture
async def mock_llm_client():
    llm = AsyncMock(spec=LLMClient)
    llm.generate_json.return_value = {
        "proposals": [
            {
                "title": "Refactor Similar Code",
                "description": "Refactor similar code to reduce redundancy.",
                "rationale": "Reduces maintenance overhead.",
                "estimated_impact": "high",
                "changes": [
                    {
                        "file_path": "skyproject/pm_ai/some_file.py",
                        "new_content": "complete new file content",
                        "change_type": "modify"
                    }
                ]
            }
        ]
    }
    return llm

@pytest.fixture
def mock_source_code():
    return {
        "file1.py": "def foo(): pass",
        "file2.py": "def foo(): pass"
    }

@pytest.mark.asyncio
async def test_analyze_self(mock_llm_client, mock_source_code):
    improver = PMSelfImprover(mock_llm_client)
    proposals = await improver.analyze_self()

    assert len(proposals) == 1
    assert proposals[0].title == "Refactor Similar Code"
    assert proposals[0].estimated_impact == "high"

@pytest.mark.asyncio
async def test_redundancy_detection(mock_source_code):
    improver = PMSelfImprover(AsyncMock(spec=LLMClient))
    analysis_results, redundancy_report, refactoring_suggestions, _ = improver._analyze_source_code(mock_source_code)

    assert "file1.py" in analysis_results
    assert "file2.py" in analysis_results
    assert "Consider refactoring" in refactoring_suggestions

@pytest.mark.asyncio
async def test_logging_in_analyze_self(mock_llm_client, caplog):
    improver = PMSelfImprover(mock_llm_client)

    with caplog.at_level(logging.INFO):
        proposals = await improver.analyze_self()

    assert "Generating self-improvement proposals." in caplog.text
    assert "Generated 1 proposals." in caplog.text
