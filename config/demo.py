"""Изолированная локальная демобаза. Не использовать для реальных данных."""
from .settings import *  # noqa: F403

DATABASES['default']['NAME'] = BASE_DIR / 'demo.sqlite3'  # noqa: F405
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
