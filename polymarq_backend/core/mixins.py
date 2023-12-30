from django.db import models


class CreatedAtMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True


class UpdatedAtMixin(models.Model):
    updated_at = models.DateTimeField(auto_now=True)

    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True


class CreatedAndUpdatedAtMixin(CreatedAtMixin, UpdatedAtMixin):
    # https://docs.djangoproject.com/en/3.2/ref/models/options/#abstract
    class Meta:
        abstract = True
