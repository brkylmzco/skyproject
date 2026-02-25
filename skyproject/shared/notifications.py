import os
import asyncio
from typing import Optional
from firebase_admin import credentials, initialize_app, messaging
from skyproject.shared.device_registration import DeviceRegistrationService
from skyproject.shared.logging_utils import log_error, log_warning, log_info, ErrorCode

# Initialize Firebase Admin SDK
cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
cred = credentials.Certificate(cred_path)
initialize_app(cred)

class NotificationService:
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    @staticmethod
    async def send_notification(token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
        """Send a push notification to a specific device using FCM token with retry logic."""
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token,
            data=data
        )

        attempt = 0
        while attempt < NotificationService.MAX_RETRIES:
            try:
                response = messaging.send(message)
                log_info(f'Successfully sent message: {response}')
                return True
            except messaging.ApiCallError as e:
                log_error(ErrorCode.FCM_API_ERROR, f'FCM API error: {str(e)}')
            except messaging.UnregisteredError as e:
                log_warning(f'{ErrorCode.UNREGISTERED_TOKEN.value} - Token no longer registered: {str(e)}')
                # Handle token removal
                DeviceRegistrationService.remove_token(token)
                return False
            except Exception as e:
                log_error(ErrorCode.GENERAL_NOTIFICATION_ERROR, f'Error sending message: {str(e)}')

            attempt += 1
            if attempt < NotificationService.MAX_RETRIES:
                await asyncio.sleep(NotificationService.RETRY_DELAY * (2 ** (attempt - 1)))
            else:
                log_error(ErrorCode.MAX_RETRIES_REACHED, f'Max retries reached. Failed to send notification to token: {token}')
                return False
        return False
