from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Встроенные пути Django для входа и выхода
    path('accounts/', include('django.contrib.auth.urls')),

    # Пути журнала
    path('', include('journal.urls')),
]