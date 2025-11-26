from xml.etree import ElementTree as ET

from django.contrib.sites.shortcuts import get_current_site
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import _get_latest_lastmod, x_robots_tag
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db import connection
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils.http import http_date

from sounds.models import Sound, Pack


class SoundSitemap(Sitemap):
    limit = 20000

    def get_latest_lastmod(self):
        latest_sound = Sound.public.order_by("-created").first()
        if latest_sound:
            return latest_sound.created
        return None

    def items(self):
        return Sound.public.select_related("user").all()

    def lastmod(self, obj: Sound):
        return obj.created


class PackSitemap(Sitemap):
    limit = 20000

    def get_latest_lastmod(self):
        latest_pack = Pack.objects.filter(is_deleted=False).order_by("-last_updated").first()
        if latest_pack:
            return latest_pack.last_updated
        return None

    def items(self):
        return (
            Pack.objects.filter(is_deleted=False)
            .select_related("user")
            .only("id", "last_updated", "user__username")
            .all()
        )

    def lastmod(self, obj: Pack):
        return obj.last_updated


sitemaps = {
    "sounds": SoundSitemap,
    "packs": PackSitemap,
}


@x_robots_tag
def sitemap_view(
    request,
    sitemaps,
    section=None,
    content_type="application/xml",
):
    # This is the same as django.contrib.sitemaps.views.sitemap, but modified to generate
    # the sitemaps using xml.etree instead of a django template.
    req_protocol = request.scheme
    req_site = get_current_site(request)

    if section is not None:
        if section not in sitemaps:
            raise Http404("No sitemap available for section: %r" % section)
        maps = [sitemaps[section]]
    else:
        maps = sitemaps.values()
    page = request.GET.get("p", 1)

    lastmod = None
    all_sites_lastmod = True
    urls = []
    for site in maps:
        try:
            if callable(site):
                site = site()
            urls.extend(site.get_urls(page=page, site=req_site, protocol=req_protocol))
            if all_sites_lastmod:
                site_lastmod = getattr(site, "latest_lastmod", None)
                if site_lastmod is not None:
                    lastmod = _get_latest_lastmod(lastmod, site_lastmod)
                else:
                    all_sites_lastmod = False
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page '%s'" % page)
    # If lastmod is defined for all sites, set header so as
    # ConditionalGetMiddleware is able to send 304 NOT MODIFIED
    if all_sites_lastmod:
        headers = {"Last-Modified": http_date(lastmod.timestamp())} if lastmod else None
    else:
        headers = None

    urlset = ET.Element(
        "urlset",
        {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9", "xmlns:xhtml": "http://www.w3.org/1999/xhtml"},
    )

    for url_info in urls:
        url = ET.SubElement(urlset, "url")
        # We know that these are the only fields we want to add
        ET.SubElement(url, "loc").text = url_info["location"]
        ET.SubElement(url, "lastmod").text = url_info["lastmod"].strftime("%Y-%m-%d")

    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="unicode")
    return HttpResponse(xml_str, content_type=content_type, headers=headers)
