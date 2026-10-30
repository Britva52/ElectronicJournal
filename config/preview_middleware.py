"""Поддержка изолированных cookies в HTTPS-предпросмотре, не для production."""
from http.cookies import Morsel

from django.conf import settings


class _PartitionedMorsel(Morsel):
    # Python 3.11 не поддерживает атрибут Partitioned в http.cookies.
    def OutputString(self, attrs=None):
        return super().OutputString(attrs) + '; Partitioned'


class PartitionedPreviewCookies:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for name in (settings.CSRF_COOKIE_NAME, settings.SESSION_COOKIE_NAME):
            cookie = response.cookies.get(name)
            if cookie and cookie['secure']:
                cookie.__class__ = _PartitionedMorsel
        return response
