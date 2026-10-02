from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    path('', views.index, name='index'),
    path('group/<int:group_id>/', views.group_journal, name='group_journal'),

    # Новый путь для выставления оценки
    path('grade/add/<int:lesson_id>/<int:student_id>/', views.add_grade, name='add_grade'),
]