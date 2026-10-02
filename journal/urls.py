from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Главная страница (путь пустой, то есть просто корень сайта)
    path('', views.index, name='index'),
]