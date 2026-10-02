from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import StudyGroup, Lesson, StudentProfile, Grade


@login_required
def index(request):
    all_groups = StudyGroup.objects.all().order_by('name')
    my_groups = []

    # Если зашел преподаватель, ищем только ТЕ группы, где он ведет занятия
    if request.user.role == 'teacher':
        # Ищем через связи: группы -> занятия -> этот преподаватель.
        # distinct() убирает дубликаты (чтобы группа не вывелась 10 раз)
        my_groups = StudyGroup.objects.filter(lesson__teacher=request.user).distinct().order_by('name')

    context = {
        'all_groups': all_groups,
        'my_groups': my_groups,
    }
    return render(request, 'journal/index.html', context)


@login_required
def group_journal(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    students = StudentProfile.objects.filter(group=group)
    lessons = Lesson.objects.filter(group=group).order_by('date')

    journal_data = []
    for student in students:
        student_grades = []
        for lesson in lessons:
            grade = Grade.objects.filter(student=student, lesson=lesson).first()
            student_grades.append({
                'lesson': lesson,
                'grade': grade
            })

        journal_data.append({
            'student': student,
            'grades': student_grades
        })

    context = {
        'group': group,
        'lessons': lessons,
        'journal_data': journal_data,
    }
    return render(request, 'journal/journal.html', context)

@login_required
def add_grade(request, lesson_id, student_id):
    if request.user.role not in ['teacher', 'admin']:
        return HttpResponseForbidden("У вас нет прав для выставления оценок.")

    lesson = get_object_or_404(Lesson, id=lesson_id)
    student = get_object_or_404(StudentProfile, id=student_id)

    if request.method == 'POST':
        value = request.POST.get('value')
        is_absent = request.POST.get('is_absent') == 'on' # Галочка "Н"

        grade, created = Grade.objects.get_or_create(
            lesson=lesson,
            student=student
        )

        if is_absent:
            grade.is_absent = True
            grade.value = None
        else:
            grade.is_absent = False
            # Если передали оценку (от 2 до 5), сохраняем её
            if value and value.isdigit():
                grade.value = int(value)
            else:
                grade.value = None

        grade.save()

        # Возвращаем пользователя обратно в журнал этой группы
        return redirect('journal:group_journal', group_id=lesson.group.id)

    return HttpResponseForbidden("Разрешен только POST-запрос.")