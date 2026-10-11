import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from apps.accounts.permissions import capabilities_of  # noqa: F401  (kept for template parity)
from apps.communication.tasks import send_email
from apps.core import audit

from .content import HOME_HIGHLIGHTS, NEWS, PAGES
from .forms import EnquiryForm

logger = logging.getLogger(__name__)
ENQUIRY_LIMIT = 5  # per IP per hour


def home(request):
    return render(request, "website/home.html", {"highlights": HOME_HIGHLIGHTS, "news": NEWS})


def page(request, slug):
    data = PAGES.get(slug)
    if data is None:
        raise Http404
    return render(request, "website/page.html", {"page": data})


def _rate_limited(ip):
    key = f"enquiry:{ip}"
    cache.add(key, 0, 3600)
    try:
        return cache.incr(key) > ENQUIRY_LIMIT
    except ValueError:
        return False  # cache unavailable: fail open, Nginx rate limiting still applies


def contact(request):
    if request.method == "POST":
        form = EnquiryForm(request.POST)
        ip = audit.client_ip(request) or "unknown"
        if _rate_limited(ip):
            messages.error(request, "Too many enquiries from your network. Please try again later.")
        elif form.is_valid():
            enquiry = form.save(commit=False)
            enquiry.ip_address = audit.client_ip(request)
            enquiry.save()
            try:
                send_email.delay(
                    f"Thank you for contacting {settings.SCHOOL_NAME}",
                    f"Dear {enquiry.name},\n\nWe received your enquiry and will reply soon.\n\n{settings.SCHOOL_NAME}",
                    [enquiry.email],
                )
            except Exception:  # noqa: BLE001  broker down must not break the form
                logger.exception("could not queue enquiry acknowledgement")
            messages.success(request, "Thank you! Your enquiry has been received.")
            return redirect("website:contact")
    else:
        form = EnquiryForm()
    return render(request, "website/contact.html", {"form": form})


@require_GET
def robots(request):
    body = "User-agent: *\nDisallow: /manage-site/\nDisallow: /accounts/\nDisallow: /metrics\n"
    body += f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml\n"
    return HttpResponse(body, content_type="text/plain")
