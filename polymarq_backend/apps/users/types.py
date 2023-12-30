from datetime import datetime

from django.db import models


class UserType(models.Model):
    uuid: str
    first_name: str
    last_name: str
    email: str
    username: str
    date_joined: datetime
    phone_number: str
    profile_picture: str
    longitude: float
    latitude: float
    is_technician: bool
    is_client: bool
    is_active: bool
    is_verified: bool

    class Meta:
        abstract = True
