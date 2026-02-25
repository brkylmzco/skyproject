import pytest
import asyncio
from unittest.mock import patch, MagicMock
from skyproject.shared.notifications import NotificationService

@pytest.mark.asyncio
async def test_send_notification_success() -> None:
    """Test successful notification sending."""
    with patch('firebase_admin.messaging.send', return_value='mock_response') as mock_send:
        result = await NotificationService.send_notification('mock_token', 'Test Title', 'Test Body')
        assert result is True
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_send_notification_retries_on_failure() -> None:
    """Test notification retries on temporary failure."""
    with patch('firebase_admin.messaging.send', side_effect=Exception('Temporary failure')) as mock_send:
        result = await NotificationService.send_notification('mock_token', 'Test Title', 'Test Body')
        assert result is False
        assert mock_send.call_count == NotificationService.MAX_RETRIES

@pytest.mark.asyncio
async def test_send_notification_handles_unregistered_token() -> None:
    """Test handling of unregistered token error."""
    from firebase_admin.messaging import UnregisteredError
    with patch('firebase_admin.messaging.send', side_effect=UnregisteredError('Token no longer registered')) as mock_send:
        with patch('skyproject.shared.device_registration.DeviceRegistrationService.remove_token') as mock_remove_token:
            result = await NotificationService.send_notification('mock_token', 'Test Title', 'Test Body')
            assert result is False
            mock_send.assert_called_once()
            mock_remove_token.assert_called_once_with('mock_token')
