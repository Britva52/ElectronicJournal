"""Настройки только для встроенного HTTPS-предпросмотра Arena.

Не применять для обычного локального запуска или эксплуатации учреждения.
"""
import os
from .settings import *  # noqa: F403

# В предпросмотре работаем только с отдельной базой, а не с основной базой проекта.
DATABASES['default']['NAME'] = os.environ.get('PORTAL_PREVIEW_DB', '/home/user/portal-preview.sqlite3')  # noqa: F405
ALLOWED_HOSTS = ['.e2b.app', '.arena.site', 'localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = ['https://*.e2b.app', 'https://*.arena.site']
# HTTPS завершается на прокси предпросмотра; эти настройки не включены в основных settings.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
# Partitioned cookies позволяют браузерам с поддержкой CHIPS использовать вход
# в стороннем iframe. Остальные браузеры могут открыть портал в отдельной вкладке.
MIDDLEWARE = ['config.preview_middleware.PartitionedPreviewCookies', *MIDDLEWARE]  # noqa: F405
CSRF_FAILURE_VIEW = 'config.preview_views.csrf_failure'
