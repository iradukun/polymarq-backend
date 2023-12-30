from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created

from polymarq_backend.core.sender import Sender

# Signal arguments: instance, reset_password_token
phone_reset_password_token_created = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    context = {
        "user": reset_password_token.user,
        # "username": reset_password_token.user.username,
        # "email": reset_password_token.user.email,
        "reset_code": reset_password_token.key,
    }

    # render email text
    # email_html_message = render_to_string("email/user_reset_password.html", context)
    # email_plaintext_message = render_to_string("email/user_reset_password.txt", context)

    Sender(
        reset_password_token.user,
        email_content_object="notification.messages.reset_password_token",
        html_template="emails/authentication/password-reset.html",
        email_notif=True,
        context=context,
    )


@receiver(phone_reset_password_token_created)
def password_reset_token_created_for_phone(sender, instance, reset_password_token, *args, **kwargs):
    # send an sms to the user phone
    Sender(
        reset_password_token.user,
        sms_notif=True,
        sms_message=f"Your Polymarq verification code is {reset_password_token.key}",
    )
