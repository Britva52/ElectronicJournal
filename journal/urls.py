from django.urls import path
from . import views

app_name = 'journal'
urlpatterns = [
    path('', views.home, name='home'),
    path('news/', views.news_list, name='news'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),
    path('library/', views.library, name='library'),
    path('schedule/', views.schedule, name='schedule'),
    path('profile/', views.profile, name='profile'),
    path('journal/', views.index, name='index'),
    path('group/<int:group_id>/', views.group_journal, name='group_journal'),
    path('grade/add/<int:lesson_id>/<int:student_id>/', views.add_grade, name='add_grade'),
]
