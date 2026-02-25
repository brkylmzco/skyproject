import pytest
from skyproject.pm_ai.self_improve import PMSelfImprover
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import ImprovementProposal, CodeChange

@pytest.fixture
async def self_improver_fixture():
    llm_client = LLMClient()
    return PMSelfImprover(llm=llm_client)

@pytest.mark.asyncio
async def test_analyze_self(self_improver_fixture):
    improver = self_improver_fixture
    proposals = await improver.analyze_self()
    assert isinstance(proposals, list)
    if proposals:
        for proposal in proposals:
            assert isinstance(proposal, ImprovementProposal)

@pytest.mark.asyncio
async def test_apply_improvement(self_improver_fixture):
    improver = self_improver_fixture
    proposal = ImprovementProposal(
        source="pm_ai",
        target="pm_ai",
        title="Test Improvement",
        description="Testing apply improvement",
        rationale="To test the apply functionality",
        estimated_impact="low",
        proposed_changes=[
            CodeChange(
                file_path="skyproject/pm_ai/test_file.py",
                new_content="print('hello world')",
                change_type="modify",
            )
        ]
    )

    result = await improver.apply_improvement(proposal)
    assert result is True or False
    assert proposal.status in ["implemented", "rejected"]
