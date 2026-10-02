from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Подключаем пути нашего журнала для главной страницы сайта
    path('', include('journal.urls')), 
]