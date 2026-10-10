from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .content import PAGES


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return ["website:home", "website:contact"] + [f"page:{s}" for s in PAGES]

    def location(self, item):
        if item.startswith("page:"):
            return reverse("website:page", kwargs={"slug": item.split(":", 1)[1]})
        return reverse(item)
