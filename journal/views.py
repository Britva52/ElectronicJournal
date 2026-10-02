from django.shortcuts import render
from .models import StudyGroup


def index(request):
    # Достаем все учебные группы из базы данных
    groups = StudyGroup.objects.all()

    # Отдаем их в HTML-шаблон
    context = {
        'groups': groups
    }
    return render(request, 'journal/index.html', context)