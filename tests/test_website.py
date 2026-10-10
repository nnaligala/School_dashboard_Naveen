import pytest
from django.urls import reverse

from apps.website.content import PAGES
from apps.website.models import Enquiry


def test_home_and_pages(client):
    assert client.get("/").status_code == 200
    for slug in PAGES:
        r = client.get(reverse("website:page", args=[slug]))
        assert r.status_code == 200
        assert b"Lorem" not in r.content


def test_unknown_page_404(client):
    assert client.get("/no-such-page/").status_code == 404


def test_robots_and_sitemap(client):
    assert b"Disallow: /manage-site/" in client.get("/robots.txt").content
    assert b"<urlset" in client.get("/sitemap.xml").content


@pytest.mark.django_db
def test_enquiry_saved_and_email_queued(client, mailoutbox):
    r = client.post("/contact/", {"name": "Asha", "email": "asha@example.com", "message": "Admissions info please"})
    assert r.status_code == 302
    assert Enquiry.objects.count() == 1
    assert len(mailoutbox) == 1  # Celery runs eagerly in tests


@pytest.mark.django_db
def test_honeypot_blocks_bots(client):
    client.post("/contact/", {"name": "Bot", "email": "b@example.com", "message": "x", "website": "http://spam"})
    assert Enquiry.objects.count() == 0


@pytest.mark.django_db
def test_enquiry_rate_limit(client):
    from django.core.cache import cache
    cache.clear()
    for i in range(7):
        client.post("/contact/", {"name": f"N{i}", "email": f"n{i}@example.com", "message": "hello"})
    assert Enquiry.objects.count() == 5


@pytest.mark.django_db
def test_health_endpoints(client):
    assert client.get("/healthz/").status_code == 200
    r = client.get("/readyz/")
    assert r.status_code == 200 and r.json()["database"] == "ok"


@pytest.mark.django_db
def test_security_headers(client):
    r = client.get("/")
    assert r["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r["Content-Security-Policy"]
