import os

from src.api.notification_api.notification_service import NotificationService

notif_service = NotificationService(os.getenv("APP_MESSAGE_TRANSPORT"))
