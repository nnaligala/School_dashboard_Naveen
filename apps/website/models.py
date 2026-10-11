from django.db import models

from apps.core.models import PublicIdModel, TimeStampedModel


class Enquiry(PublicIdModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(max_length=2000)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.name} <{self.email}>"
