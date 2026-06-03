import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin App lazily
_firebase_app_initialized = False

def initialize_firebase():
    global _firebase_app_initialized
    if _firebase_app_initialized:
        return True

    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
    
    if not cred_path or not os.path.exists(cred_path):
        logger.warning(f"Firebase credentials not found at: {cred_path}. Push notifications will be disabled.")
        return False

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _firebase_app_initialized = True
        logger.info("Firebase Admin initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin: {e}")
        return False

def send_push_notification(user, title, body, data=None):
    """
    Sends a push notification to a specific user using Firebase Cloud Messaging.
    """
    if not initialize_firebase():
        return False

    if not user or not getattr(user, 'fcm_token', None):
        logger.warning(f"User {getattr(user, 'username', 'Unknown')} does not have an FCM token.")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=user.fcm_token,
        )
        
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True
    except Exception as e:
        logger.error(f"Error sending message to {user.username}: {e}")
        return False
