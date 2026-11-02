"""Вымышленные данные для локальной демонстрации — не импорт официального расписания."""
import os
from datetime import date, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from journal.models import Grade, Lesson, StudentProfile, StudyGroup, Subject


class Command(BaseCommand):
    help = 'Добавить демонстрационные группы и пример одной недели по скриншоту в отдельную демобазу.'

    def add_arguments(self, parser):
        parser.add_argument('--week', help='Любая дата демонстрационной недели в формате ГГГГ-ММ-ДД (по умолчанию текущая)')

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, 'ALLOW_EXAMPLE_SCHEDULE', False):
            raise CommandError('Команда разрешена только с --settings=config.demo. Не применяйте демоданные к рабочей базе.')
        password = os.environ.get('DEMO_PASSWORD', '')
        if len(password) < 8:
            raise CommandError('Укажите DEMO_PASSWORD не короче 8 символов.')
        try:
            selected = date.fromisoformat(options['week']) if options['week'] else timezone.localdate()
            if not 1901 <= selected.year <= 2098:
                raise ValueError
        except ValueError:
            raise CommandError('Неделя должна быть датой в формате ГГГГ-ММ-ДД.')
        monday = selected - timedelta(days=selected.weekday())
        User = get_user_model()
        group_names = ['о-П-923/1', 'о-П-923/2', 'о-П-923/3', 'о-Э-923/1', 'о-Э-923/2', 'о-Э-923/3', 'о-П-1124', 'о-П-924/1']
        groups = {name: StudyGroup.objects.get_or_create(name=name)[0] for name in group_names}
        student = User.objects.filter(username='demo_923_student').first()
        if student:
            profile = StudentProfile.objects.filter(user=student, group=groups['о-П-923/3']).first()
            if student.role != 'student' or not profile:
                raise CommandError('Логин demo_923_student занят другой учётной записью. Данные не изменены.')
        else:
            student = User.objects.create_user(username='demo_923_student', password=password, role='student', first_name='Демо', last_name='Студент')
            profile = StudentProfile.objects.create(user=student, group=groups['о-П-923/3'])
        teacher = User.objects.filter(username='demo_schedule_teacher').first()
        if teacher and teacher.role != 'teacher':
            raise CommandError('Логин demo_schedule_teacher занят другой учётной записью. Данные не изменены.')
        if not teacher:
            teacher = User.objects.create_user(username='demo_schedule_teacher', password=password, role='teacher', first_name='Демо', last_name='Преподаватель')
        # Содержимое адаптировано по изображению, без утверждения, что оно актуально.
        entries = [
            (0, 2, 'Математическое моделирование', '311'), (0, 3, 'Собрание группы', '218, 2-й корпус'),
            (0, 4, 'Иностранный язык в профессиональной деятельности', '208, 1-й корпус; 103'), (0, 5, 'Физическая культура', ''),
            (1, 4, 'Численные методы', '311'), (1, 5, 'Математическое моделирование', '311'),
            (2, 2, 'Основы философии', 'онлайн'), (2, 3, 'Основы философии', 'онлайн'),
            (2, 5, 'Иностранный язык в профессиональной деятельности', 'онлайн'),
            (3, 3, 'Технология разработки и защиты баз данных', '208, 2-й корпус'),
            (3, 4, 'Инструментальные средства разработки программного обеспечения', '208, 2-й корпус'),
            (3, 5, 'Стандартизация, сертификация и техническое документоведение', '311'),
            (3, 6, 'Стандартизация, сертификация и техническое документоведение', '311'),
            (4, 5, 'Технология разработки и защиты баз данных', '208, 2-й корпус'),
            (4, 6, 'Инструментальные средства разработки программного обеспечения', '208, 2-й корпус'),
            (5, 4, 'Численные методы', '311'), (5, 5, 'Информационная безопасность', '212, 2-й корпус'),
            (5, 6, 'Информационная безопасность', '212, 2-й корпус'),
        ]
        times = {2: (time(10, 10), time(11, 40)), 3: (time(12, 10), time(13, 40)),
                 4: (time(13, 50), time(15, 20)), 5: (time(15, 40), time(17, 10)), 6: (time(17, 20), time(18, 50))}
        subjects = {}
        first_lesson = None
        for day, number, title, room in entries:
            if title not in subjects:
                subjects[title] = Subject.objects.get_or_create(name=title)[0]
            for group_name in ('о-П-923/3', 'о-П-1124'):
                # Не перезаписываем и не дублируем уже существующие занятия в этом слоте.
                day_date = monday + timedelta(days=day)
                if Lesson.objects.filter(group=groups[group_name], date=day_date, start_time=times[number][0]).exists():
                    continue
                lesson = Lesson.objects.create(group=groups[group_name], date=day_date,
                    subject=subjects[title], teacher=teacher, start_time=times[number][0], end_time=times[number][1],
                    room=room, topic='Демонстрационный пример по скриншоту; требуется проверка')
                if first_lesson is None and group_name == 'о-П-923/3':
                    first_lesson = lesson
        if first_lesson:
            Grade.objects.get_or_create(lesson=first_lesson, student=profile, defaults={'value': 85})
        self.stdout.write(self.style.SUCCESS(f'Пример добавлен для недели с {monday:%d.%m.%Y}; занятые слоты пропущены. Это не официальное расписание.'))
