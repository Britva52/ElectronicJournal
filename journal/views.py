from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import StudyGroup, Lesson, StudentProfile, Grade, GradeChange, News, LibraryResource


def home(request):
    news = News.objects.filter(is_published=True, published_at__lte=timezone.now())[:5]
    return render(request, 'journal/home.html', {'news': news})


def news_list(request):
    news = News.objects.filter(is_published=True, published_at__lte=timezone.now())
    return render(request, 'journal/news.html', {'page': Paginator(news, 10).get_page(request.GET.get('page'))})


def news_detail(request, pk):
    item = get_object_or_404(News, pk=pk, is_published=True, published_at__lte=timezone.now())
    return render(request, 'journal/news_detail.html', {'item': item})


def library(request):
    resources = LibraryResource.objects.filter(is_published=True).select_related('subject')
    query = request.GET.get('q', '').strip()
    if query:
        resources = resources.filter(title__icontains=query)
    return render(request, 'journal/library.html', {'page': Paginator(resources, 20).get_page(request.GET.get('page')), 'query': query})


def student_group(user):
    profile = StudentProfile.objects.filter(user=user).select_related('group').first()
    return profile.group if profile else None


@login_required
def schedule(request):
    today = timezone.localdate()
    try:
        selected = date.fromisoformat(request.GET.get('week', '')) if request.GET.get('week') else today
        if not 1901 <= selected.year <= 2098:
            raise ValueError
    except ValueError:
        return HttpResponseBadRequest('Некорректная дата недели.')
    monday = selected - timedelta(days=selected.weekday())
    lessons = Lesson.objects.select_related('group', 'subject', 'teacher').filter(
        date__gte=monday, date__lt=monday + timedelta(days=7)
    ).order_by('date', 'start_time', 'pk')
    group = None
    groups = StudyGroup.objects.none()
    if request.user.role == 'student':
        group = student_group(request.user)
        lessons = lessons.filter(group=group) if group else lessons.none()
    elif request.user.role == 'teacher':
        lessons = lessons.filter(teacher=request.user)
    else:
        groups = StudyGroup.objects.order_by('name')
        group_id = request.GET.get('group', '')
        if group_id:
            if not group_id.isascii() or not group_id.isdigit() or len(group_id) > 9:
                return HttpResponseBadRequest('Некорректная группа.')
            group = get_object_or_404(StudyGroup, pk=int(group_id))
            lessons = lessons.filter(group=group)
    day_names = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')
    days = [{'date': monday + timedelta(days=i), 'name': name, 'lessons': []} for i, name in enumerate(day_names)]
    numbers = {'08:30': '1', '10:10': '2', '12:10': '3', '13:50': '4', '15:40': '5', '17:20': '6'}
    for lesson in lessons:
        lesson.display_number = numbers.get(lesson.start_time.strftime('%H:%M')) if lesson.start_time else None
        days[(lesson.date - monday).days]['lessons'].append(lesson)
    return render(request, 'journal/schedule.html', {
        'days': days, 'today': today, 'week_start': monday, 'week_end': monday + timedelta(days=6),
        'previous_week': monday - timedelta(days=7), 'next_week': monday + timedelta(days=7),
        'group': group, 'groups': groups,
    })


@login_required
def profile(request):
    group = student_group(request.user) if request.user.role == 'student' else None
    return render(request, 'journal/profile.html', {'group': group})


@login_required
def index(request):
    all_groups = StudyGroup.objects.all().order_by('name')
    if request.user.role == 'student':
        group = student_group(request.user)
        all_groups = all_groups.filter(pk=group.pk) if group else all_groups.none()
    my_groups = StudyGroup.objects.filter(lesson__teacher=request.user).distinct().order_by('name') if request.user.role == 'teacher' else []
    return render(request, 'journal/index.html', {'all_groups': all_groups, 'my_groups': my_groups})


@login_required
def group_journal(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    if request.user.role == 'student' and not StudentProfile.objects.filter(user=request.user, group=group).exists():
        return HttpResponseForbidden('У вас нет доступа к журналу этой группы.')
    students = list(StudentProfile.objects.filter(Q(group=group) | Q(grades__lesson__group=group)).distinct().select_related('user').order_by('user__last_name', 'user__first_name', 'pk'))
    lessons = list(Lesson.objects.filter(group=group).select_related('subject').order_by('date', 'pk'))
    grades = {(g.student_id, g.lesson_id): g for g in Grade.objects.filter(lesson__group=group)}
    journal_data = [{'student': student, 'grades': [{'lesson': lesson, 'grade': grades.get((student.pk, lesson.pk)), 'can_edit': student.group_id == group.pk and (request.user.role == 'admin' or (request.user.role == 'teacher' and lesson.teacher_id == request.user.pk))} for lesson in lessons]} for student in students]
    return render(request, 'journal/journal.html', {'group': group, 'students': students, 'lessons': lessons, 'journal_data': journal_data})


@login_required
@require_POST
def add_grade(request, lesson_id, student_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    student = get_object_or_404(StudentProfile, id=student_id, group=lesson.group)
    if not (request.user.role == 'admin' or (request.user.role == 'teacher' and lesson.teacher_id == request.user.pk)):
        return HttpResponseForbidden('У вас нет прав для выставления оценок.')
    value = request.POST.get('value', '').strip()
    is_absent = request.POST.get('is_absent') == 'on'
    if not is_absent and value and (not value.isascii() or not value.isdigit() or len(value) > 3 or not 1 <= int(value) <= 100):
        return HttpResponseBadRequest('Оценка должна быть целым числом от 1 до 100.')
    new_state = 'Н' if is_absent else str(int(value)) if value else '—'
    # Блокировка занятия сериализует изменения его оценок в СУБД с поддержкой row locks.
    with transaction.atomic():
        Lesson.objects.select_for_update().get(pk=lesson.pk)
        grade = Grade.objects.filter(lesson=lesson, student=student).first()
        old_state = ('Н' if grade.is_absent else str(grade.value)) if grade else '—'
        if old_state != new_state:
            if new_state == '—':
                if grade:
                    grade.delete()
            else:
                Grade.objects.update_or_create(lesson=lesson, student=student, defaults={'value': None if is_absent else int(value), 'is_absent': is_absent})
            GradeChange.objects.create(
                actor=request.user, actor_name=request.user.username,
                student_name=student.user.username,
                lesson_description=f'{lesson.subject} / {lesson.group} / {lesson.date} / #{lesson.pk}',
                old_state=old_state, new_state=new_state,
            )
    return redirect('journal:group_journal', group_id=lesson.group_id)
