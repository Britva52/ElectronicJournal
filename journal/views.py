from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import StudyGroup, Lesson, StudentProfile, Grade, GradeChange, News, LibraryResource, ScheduleReference, Subject
from .forms import ProfileContactForm


def home(request):
    news = News.objects.filter(is_published=True, published_at__lte=timezone.now())[:5]
    return render(request, 'journal/home.html', {'news': news})


def pagination_query(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def news_list(request):
    news = News.objects.filter(is_published=True, published_at__lte=timezone.now())
    query = request.GET.get('q', '').strip()[:200]
    if query:
        news = news.filter(Q(title__icontains=query) | Q(content__icontains=query))
    return render(request, 'journal/news.html', {'page': Paginator(news, 10).get_page(request.GET.get('page')), 'query': query, 'page_query': pagination_query(request)})


def news_detail(request, pk):
    item = get_object_or_404(News, pk=pk, is_published=True, published_at__lte=timezone.now())
    return render(request, 'journal/news_detail.html', {'item': item})


def library(request):
    published = LibraryResource.objects.filter(is_published=True)
    resources = published.select_related('subject')
    query = request.GET.get('q', '').strip()[:200]
    subject_id = request.GET.get('subject', '')
    if query:
        resources = resources.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if subject_id:
        if not subject_id.isascii() or not subject_id.isdigit() or len(subject_id) > 9:
            return HttpResponseBadRequest('Некорректный предмет.')
        resources = resources.filter(subject_id=int(subject_id))
    subjects = Subject.objects.filter(libraryresource__is_published=True).distinct().order_by('name', 'pk')
    return render(request, 'journal/library.html', {'page': Paginator(resources, 12).get_page(request.GET.get('page')), 'query': query, 'subject_id': subject_id, 'subjects': subjects, 'page_query': pagination_query(request)})


def is_journal_admin(user):
    return user.role == 'admin' or user.is_superuser


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
    all_lessons = Lesson.objects.select_related('group', 'subject', 'teacher')
    groups = StudyGroup.objects.order_by('name')
    group = None
    group_id = request.GET.get('group', '')
    if group_id:
        if not group_id.isascii() or not group_id.isdigit() or len(group_id) > 9:
            return HttpResponseBadRequest('Некорректная группа.')
        group = get_object_or_404(StudyGroup, pk=int(group_id))
        all_lessons = all_lessons.filter(group=group)
    elif request.user.role == 'student' and not is_journal_admin(request.user):
        group = student_group(request.user)
        all_lessons = all_lessons.filter(group=group) if group else all_lessons.none()
    elif request.user.role == 'teacher' and not is_journal_admin(request.user):
        all_lessons = all_lessons.filter(teacher=request.user)
    lessons = all_lessons.filter(date__gte=monday, date__lt=monday + timedelta(days=7)).order_by('date', 'start_time', 'pk')
    closest_date = None
    if not lessons.exists():
        future = all_lessons.filter(date__gte=monday + timedelta(days=7)).order_by('date').values_list('date', flat=True).first()
        past = all_lessons.filter(date__lt=monday).order_by('-date').values_list('date', flat=True).first()
        closest_date = min((d for d in (future, past) if d), key=lambda d: abs((d - monday).days), default=None)
    closest_week = closest_date - timedelta(days=closest_date.weekday()) if closest_date else None
    day_names = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')
    days = [{'date': monday + timedelta(days=i), 'name': name, 'lessons': []} for i, name in enumerate(day_names)]
    numbers = {'08:30': '1', '10:10': '2', '12:10': '3', '13:50': '4', '15:40': '5', '17:20': '6'}
    for lesson in lessons:
        lesson.display_number = numbers.get(lesson.start_time.strftime('%H:%M')) if lesson.start_time else None
        days[(lesson.date - monday).days]['lessons'].append(lesson)
    has_lessons = any(day['lessons'] for day in days)
    references = list(ScheduleReference.objects.filter(group=group).order_by('weekday', 'number')) if group else []
    show_reference = bool(references) and (not has_lessons or request.GET.get('reference') == '1')
    if show_reference:
        for entry in references:
            days[entry.weekday].setdefault('references', []).append(entry)
    return render(request, 'journal/schedule.html', {
        'show_reference': show_reference, 'has_reference': bool(references),
        'days': days, 'today': today, 'week_start': monday, 'week_end': monday + timedelta(days=6),
        'previous_week': monday - timedelta(days=7), 'next_week': monday + timedelta(days=7),
        'group': group, 'groups': groups, 'closest_week': closest_week, 'has_lessons': has_lessons,
        'has_unverified_lessons': any('По скриншоту: дата и актуальность требуют проверки.' in lesson.topic for day in days for lesson in day['lessons']),
        'journal_admin': is_journal_admin(request.user),
    })


@login_required
def profile(request):
    group = student_group(request.user) if request.user.role == 'student' else None
    return render(request, 'journal/profile.html', {'group': group})


@login_required
def edit_profile(request):
    form = ProfileContactForm(request.POST if request.method == 'POST' else None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Контактные данные сохранены.')
        return redirect('journal:profile')
    return render(request, 'journal/profile_edit.html', {'form': form})


@login_required
def index(request):
    all_groups = StudyGroup.objects.all().order_by('name')
    if request.user.role == 'student' and not is_journal_admin(request.user):
        group = student_group(request.user)
        all_groups = all_groups.filter(pk=group.pk) if group else all_groups.none()
    my_groups = StudyGroup.objects.filter(lesson__teacher=request.user).distinct().order_by('name') if request.user.role == 'teacher' else []
    return render(request, 'journal/index.html', {'all_groups': all_groups, 'my_groups': my_groups})


@login_required
def group_journal(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    if request.user.role == 'student' and not is_journal_admin(request.user) and not StudentProfile.objects.filter(user=request.user, group=group).exists():
        return HttpResponseForbidden('У вас нет доступа к журналу этой группы.')
    students = list(StudentProfile.objects.filter(Q(group=group) | Q(grades__lesson__group=group)).distinct().select_related('user').order_by('user__last_name', 'user__first_name', 'pk'))
    lessons = list(Lesson.objects.filter(group=group).select_related('subject').order_by('date', 'pk'))
    grades = {(g.student_id, g.lesson_id): g for g in Grade.objects.filter(lesson__group=group)}
    journal_data = [{'student': student, 'grades': [{'lesson': lesson, 'grade': grades.get((student.pk, lesson.pk)), 'can_edit': student.group_id == group.pk and (is_journal_admin(request.user) or (request.user.role == 'teacher' and lesson.teacher_id == request.user.pk))} for lesson in lessons]} for student in students]
    return render(request, 'journal/journal.html', {'group': group, 'students': students, 'lessons': lessons, 'journal_data': journal_data})


@login_required
@require_POST
def add_grade(request, lesson_id, student_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    student = get_object_or_404(StudentProfile, id=student_id, group=lesson.group)
    if not (is_journal_admin(request.user) or (request.user.role == 'teacher' and lesson.teacher_id == request.user.pk)):
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
