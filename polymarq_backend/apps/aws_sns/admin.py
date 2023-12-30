from django.contrib import admin

from polymarq_backend.apps.aws_sns.models import Device, Log

admin.site.register(Device)
admin.site.register(Log)
