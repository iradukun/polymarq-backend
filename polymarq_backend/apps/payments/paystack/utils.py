from rest_framework.exceptions import ValidationError


def validate_paystack_response(func):
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if not 200 <= response.status_code < 400:
            raise ValidationError(f"Paystack failed with error code: {response.status_code}")

        return response.json()

    return wrapper
