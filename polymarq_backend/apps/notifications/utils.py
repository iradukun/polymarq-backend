from polymarq_backend.apps.aws_sns.models import Device
from polymarq_backend.apps.aws_sns.tasks import refresh_device
from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.users.models import User
from polymarq_backend.core.sender import Sender


def send_push_notifications(
    recipient: User,
    notification_type: str,
    title: str,
    body: str,
    push_notif_data: None | dict = None,
) -> Notification:
    """
    Send Mobile Push Notification

    Args:
        recipient (User): The notification's recipient
        notification_type (str): The type of notification
        title (str): The notification's Title
        body (str): The notification's body
    """
    devices = Device.objects.filter(user=recipient)

    for device in devices:
        refresh_device(device)  # refreshing the device to make sure it is enabled and ready to use.

        if device.active and device.arn:
            Sender(
                user_account=recipient,
                device=device,
                notification_type=notification_type,
                text=body,
                data=push_notif_data if not push_notif_data else {"title": title, "body": body},
                title=title,
                push_notif=True,
            )

    # log notification
    notif = Notification.objects.create(
        title=title,
        body=body,
        recipient=recipient,
        notification_type=notification_type,
        payload=push_notif_data if push_notif_data else None,
    )
    return notif
