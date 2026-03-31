import logging
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None):
    if not user.fcm_token:
        logger.warning(f"No FCM token for user {user.id}")
        return None

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={k: str(v) for k, v in (data or {}).items()},
        token=user.fcm_token,

        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                click_action="FLUTTER_NOTIFICATION_CLICK"
            )
        ),

        apns=messaging.APNSConfig(
            headers={"apns-priority": "10"},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    category="FLUTTER_NOTIFICATION_CLICK"
                )
            )
        )
    )

    try:
        response = messaging.send(message)
        logger.info(f"Push sent to user {user.id}: {response}")
        return response

    except messaging.UnregisteredError:
        logger.error(f"Token invalid for user {user.id}")
        user.fcm_token = None
        user.save(update_fields=['fcm_token'])
        return None

    except messaging.SenderIdMismatchError:
        logger.error(f"Sender mismatch for user {user.id}")
        user.fcm_token = None
        user.save(update_fields=['fcm_token'])
        return None

    except FirebaseError as e:
        logger.error(f"Firebase error: {str(e)}")
        return None

    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return None