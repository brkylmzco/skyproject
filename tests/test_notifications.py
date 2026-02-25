import unittest
from unittest.mock import patch
from skyproject.shared.notifications import NotificationService

class TestNotificationService(unittest.TestCase):
    @patch('skyproject.shared.notifications.messaging.send')
    def test_send_notification_success(self, mock_send):
        mock_send.return_value = 'mock_response'
        result = NotificationService.send_notification('test_token', 'Test Title', 'Test Body')
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch('skyproject.shared.notifications.messaging.send', side_effect=Exception('Test Error'))
    def test_send_notification_failure(self, mock_send):
        result = NotificationService.send_notification('test_token', 'Test Title', 'Test Body')
        self.assertFalse(result)
        mock_send.assert_called_once()

if __name__ == '__main__':
    unittest.main()