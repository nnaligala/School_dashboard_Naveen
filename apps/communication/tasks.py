from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(
    name="apps.communication.tasks.send_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=60,
    time_limit=90,
)
def send_email(subject, body, to):
    """Send one email. Routed to the `email` queue; retries with exponential backoff."""
    return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, list(to), fail_silently=False)
