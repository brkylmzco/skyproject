import os
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from requests.exceptions import ConnectionError, Timeout
from skyproject.shared.llm_client import LLMClient

@pytest.fixture
async def mock_openai_client() -> AsyncMock:
    """Fixture to mock OpenAI client."""
    with patch('openai.OpenAI') as mock_openai:
        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='response'))]))
        yield mock_instance

@pytest.fixture
async def mock_anthropic_client() -> AsyncMock:
    """Fixture to mock Anthropic client."""
    with patch('anthropic.Anthropic') as mock_anthropic:
        mock_instance = mock_anthropic.return_value
        mock_instance.messages.create = AsyncMock(return_value=MagicMock(content=[MagicMock(text='response')]))
        yield mock_instance

@pytest.mark.asyncio
async def test_generate_openai_returns_expected_response(mock_openai_client: AsyncMock) -> None:
    """Test OpenAI client generates the expected response."""
    client = LLMClient(provider='openai')
    response = await client.generate('system prompt', 'user prompt')
    mock_openai_client.chat.completions.create.assert_called_once()
    assert response == 'response'

@pytest.mark.asyncio
async def test_generate_anthropic_returns_expected_response(mock_anthropic_client: AsyncMock) -> None:
    """Test Anthropic client generates the expected response."""
    client = LLMClient(provider='anthropic')
    response = await client.generate('system prompt', 'user prompt')
    mock_anthropic_client.messages.create.assert_called_once()
    assert response == 'response'

@pytest.mark.asyncio
async def test_generate_with_unknown_provider_raises_value_error() -> None:
    """Test generation with an unknown provider raises ValueError."""
    client = LLMClient(provider='unknown')
    with pytest.raises(ValueError, match='Unknown provider: unknown'):
        await client.generate('system prompt', 'user prompt')

@pytest.mark.asyncio
async def test_generate_with_retries_succeeds_after_failure(mock_openai_client: AsyncMock) -> None:
    """Test generation retries and succeeds after initial failure."""
    mock_openai_client.chat.completions.create.side_effect = [Exception('Error'), MagicMock(choices=[MagicMock(message=MagicMock(content='retry response'))])]
    client = LLMClient(provider='openai', max_retries=2)
    response = await client.generate('system prompt', 'user prompt')
    assert response == 'retry response'

@pytest.mark.asyncio
async def test_generate_json_openai_parses_correctly(mock_openai_client: AsyncMock) -> None:
    """Test OpenAI JSON response is parsed correctly."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content='{ "key": "value" }'))])
    client = LLMClient(provider='openai')
    response = await client.generate_json('system prompt', 'user prompt')
    assert response == {"key": "value"}

@pytest.mark.asyncio
async def test_generate_json_with_invalid_json_raises_json_decode_error(mock_openai_client: AsyncMock) -> None:
    """Test invalid JSON raises JSONDecodeError."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content='invalid json'))])
    client = LLMClient(provider='openai')
    with pytest.raises(json.JSONDecodeError):
        await client.generate_json('system prompt', 'user prompt')

@pytest.mark.asyncio
async def test_generate_handles_network_failure_gracefully(mock_openai_client: AsyncMock) -> None:
    """Test network failure is handled gracefully."""
    mock_openai_client.chat.completions.create.side_effect = ConnectionError('Network failure')
    client = LLMClient(provider='openai')
    with pytest.raises(ConnectionError, match='Network failure'):
        await client.generate('system prompt', 'user prompt')

@pytest.mark.asyncio
async def test_generate_handles_timeout_failure_gracefully(mock_openai_client: AsyncMock) -> None:
    """Test timeout failure is handled gracefully."""
    mock_openai_client.chat.completions.create.side_effect = Timeout('Timeout occurred')
    client = LLMClient(provider='openai')
    with pytest.raises(Timeout, match='Timeout occurred'):
        await client.generate('system prompt', 'user prompt')

@pytest.mark.asyncio
async def test_generate_with_custom_temperature(mock_openai_client: AsyncMock) -> None:
    """Test custom temperature is applied in request."""
    client = LLMClient(provider='openai', temperature=0.5)
    await client.generate('system prompt', 'user prompt')
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': 'system prompt'},
            {'role': 'user', 'content': 'user prompt'},
        ],
        temperature=0.5,
        max_tokens=4096
    )

@pytest.mark.asyncio
async def test_generate_with_custom_model(mock_openai_client: AsyncMock) -> None:
    """Test custom model is applied in request."""
    client = LLMClient(provider='openai', model='gpt-3')
    await client.generate('system prompt', 'user prompt')
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model='gpt-3',
        messages=[
            {'role': 'system', 'content': 'system prompt'},
            {'role': 'user', 'content': 'user prompt'},
        ],
        temperature=0.7,
        max_tokens=4096
    )

@pytest.mark.asyncio
async def test_generate_openai_empty_response(mock_openai_client: AsyncMock) -> None:
    """Test OpenAI handles empty response correctly."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content=''))])
    client = LLMClient(provider='openai')
    response = await client.generate('system prompt', 'user prompt')
    assert response == ''

@pytest.mark.asyncio
async def test_generate_anthropic_empty_response(mock_anthropic_client: AsyncMock) -> None:
    """Test Anthropic handles empty response correctly."""
    mock_anthropic_client.messages.create.return_value = MagicMock(content=[MagicMock(text='')])
    client = LLMClient(provider='anthropic')
    response = await client.generate('system prompt', 'user prompt')
    assert response == ''

@pytest.mark.asyncio
async def test_generate_reaching_max_retries_logs_error(mock_openai_client: AsyncMock) -> None:
    """Test reaching max retries logs error properly."""
    mock_openai_client.chat.completions.create.side_effect = ConnectionError('Persistent Network Error')
    client = LLMClient(provider='openai', max_retries=3)
    with pytest.raises(ConnectionError, match='Persistent Network Error'):
        await client.generate('system prompt', 'user prompt')
