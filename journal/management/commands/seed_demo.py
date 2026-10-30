import os
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from journal.models import Grade, Lesson, LibraryResource, News, StudentProfile, StudyGroup, Subject


class Command(BaseCommand):
    help = 'Добавляет вымышленные данные для демонстрации (используйте только отдельную тестовую базу).'

    def add_arguments(self, parser):
        parser.add_argument('--confirm-demo-database', action='store_true', help='Подтверждение, что база предназначена только для демонстрации')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm_demo_database']:
            raise CommandError('Используйте отдельную демонстрационную базу и укажите --confirm-demo-database.')
        password = os.environ.get('DEMO_PASSWORD')
        if not password or len(password) < 8:
            raise CommandError('Задайте переменную DEMO_PASSWORD длиной не менее 8 символов.')
        User = get_user_model()
        names = ['demo_admin', 'demo_teacher', 'demo_student', 'demo_student2', 'demo_student3', 'demo_teacher2']
        if User.objects.filter(username__in=names).exists():
            raise CommandError('Демо-пользователи уже существуют. Команда ничего не изменила.')

        admin = User.objects.create_superuser(username='demo_admin', password=password, role='admin', first_name='Анна', last_name='Администратор')
        teacher = User.objects.create_user(username='demo_teacher', password=password, role='teacher', first_name='Елена', last_name='Соколова')
        teacher2 = User.objects.create_user(username='demo_teacher2', password=password, role='teacher', first_name='Алексей', last_name='Морозов')
        students = [User.objects.create_user(username=username, password=password, role='student', first_name=first, last_name=last) for username, first, last in [
            ('demo_student', 'Александр', 'Иванов'), ('demo_student2', 'Мария', 'Петрова'), ('demo_student3', 'Даниил', 'Кузнецов')]]
        group, _ = StudyGroup.objects.get_or_create(name='ДЕМО-ИСП-21')
        other_group, _ = StudyGroup.objects.get_or_create(name='ДЕМО-ИСП-22')
        profiles = [StudentProfile.objects.create(user=student, group=group) for student in students]
        programming, _ = Subject.objects.get_or_create(name='Основы программирования')
        databases, _ = Subject.objects.get_or_create(name='Базы данных')
        maths, _ = Subject.objects.get_or_create(name='Математика')
        today = timezone.localdate()
        lesson_specs = [
            (-5, programming, teacher, 'Переменные и типы данных', time(9, 0), time(10, 30), '304'),
            (-3, programming, teacher, 'Условия и циклы', time(10, 45), time(12, 15), '304'),
            (0, programming, teacher, 'Функции и работа с данными', time(9, 0), time(10, 30), '304'),
            (1, databases, teacher2, 'Основы реляционных баз данных', time(10, 45), time(12, 15), '216'),
            (2, maths, teacher2, 'Элементы математического анализа', time(9, 0), time(10, 30), '205'),
            (3, programming, teacher, 'Практическая работа: функции', time(10, 45), time(12, 15), '304'),
        ]
        lessons = [Lesson.objects.create(group=group, date=today + timedelta(days=offset), subject=subject, teacher=person, topic=topic, start_time=start, end_time=end, room=room) for offset, subject, person, topic, start, end, room in lesson_specs]
        Lesson.objects.create(group=other_group, date=today + timedelta(days=1), subject=programming, teacher=teacher, topic='Введение в алгоритмы', start_time=time(13, 0), end_time=time(14, 30), room='304')
        for profile, first, second in zip(profiles, [85, 92, 76], [90, 88, 80]):
            Grade.objects.create(lesson=lessons[0], student=profile, value=first)
            Grade.objects.create(lesson=lessons[1], student=profile, value=second)
        Grade.objects.create(lesson=lessons[2], student=profiles[2], is_absent=True)
        for title, content, days in [
            ('Добро пожаловать на учебный портал!', 'Это демонстрационный пример новости. Здесь учебное заведение сможет публиковать объявления, важные даты и события для студентов и преподавателей.', 0),
            ('Неделя информационных технологий', 'Приглашаем студентов на открытые лекции и практические занятия по программированию, базам данных и цифровым технологиям. Программа мероприятия появится на портале.', 2),
            ('Учебные материалы уже в библиотеке', 'В разделе библиотеки собраны полезные ссылки для самостоятельной работы. Преподаватели могут дополнять подборку учебными материалами по своим предметам.', 5),
        ]:
            News.objects.create(title=title, content=content, published_at=timezone.now() - timedelta(days=days), is_published=True)
        for title, description, subject, url in [
            ('Документация Python', 'Официальное руководство и справочник по языку Python.', programming, 'https://docs.python.org/3/'),
            ('SQL: учебные материалы PostgreSQL', 'Введение в SQL и работа с реляционными базами данных.', databases, 'https://www.postgresql.org/docs/current/tutorial-sql.html'),
            ('Открытый учебник по математике', 'Бесплатные материалы для изучения различных разделов математики.', maths, 'https://openstax.org/subjects/math'),
        ]:
            LibraryResource.objects.create(title=title, description=description, subject=subject, url=url, is_published=True)
        self.stdout.write(self.style.SUCCESS('Демонстрационные данные созданы. Все люди и события вымышлены.'))
