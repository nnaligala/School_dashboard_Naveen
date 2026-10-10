from django.contrib.sitemaps.views import sitemap
from django.urls import path

from . import views
from .sitemaps import StaticSitemap

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.contact, name="contact"),
    path("robots.txt", views.robots, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": {"static": StaticSitemap}}, name="sitemap"),
    path("<slug:slug>/", views.page, name="page"),
]
