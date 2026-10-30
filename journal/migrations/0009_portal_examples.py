from django.db import migrations
from django.utils import timezone


def create_examples(apps, schema_editor):
    db = schema_editor.connection.alias
    News = apps.get_model('journal', 'News')
    Resource = apps.get_model('journal', 'LibraryResource')
    Subject = apps.get_model('journal', 'Subject')
    # Явно обозначенные демонстрационные записи; не выдаём их за новости колледжа.
    examples = [
        ('[Пример] Добро пожаловать на учебный портал', 'Это пример публикации для курсового проекта. В этом разделе администратор сможет размещать новости, объявления и важную информацию для студентов и преподавателей.'),
        ('[Пример] Как пользоваться электронным журналом', 'Откройте раздел «Электронный журнал», выберите группу и просмотрите оценки по занятиям. Преподаватель может внести отметку на своём занятии, а администратор — управлять данными через админ-панель.'),
        ('[Пример] Где найти расписание', 'В разделе «Расписание» можно выбрать учебную группу и перейти к нужной неделе. Даты и изменения занятий следует уточнять в учебной части.'),
        ('[Пример] Учебные материалы в библиотеке', 'В библиотеке собраны ссылки на материалы для самостоятельной работы. Используйте поиск или фильтр по предмету. Администратор может добавлять и скрывать материалы через админ-панель.'),
    ]
    for title, content in examples:
        News.objects.using(db).get_or_create(title=title, defaults={
            'content': content, 'published_at': timezone.now(), 'is_published': True,
        })
    resources = [
        ('[Пример] Python: официальная документация', 'Справочник языка Python и учебное руководство.', 'Программирование', 'https://docs.python.org/3/'),
        ('[Пример] Django: документация', 'Руководства по созданию веб-приложений на Django.', 'Программирование', 'https://docs.djangoproject.com/'),
        ('[Пример] PostgreSQL: введение в SQL', 'Основы работы с реляционными базами данных и SQL.', 'Базы данных', 'https://www.postgresql.org/docs/current/tutorial-sql.html'),
        ('[Пример] MDN: веб-технологии', 'Справочные материалы по HTML, CSS и JavaScript.', 'Веб-разработка', 'https://developer.mozilla.org/ru/'),
        ('[Пример] Git: руководство', 'Официальная книга по системе контроля версий Git.', 'Программирование', 'https://git-scm.com/book/ru/v2'),
    ]
    for title, description, subject_name, url in resources:
        subject = Subject.objects.using(db).filter(name=subject_name).order_by('pk').first()
        if subject is None:
            subject = Subject.objects.using(db).create(name=subject_name)
        Resource.objects.using(db).get_or_create(title=title, defaults={
            'description': description, 'subject': subject, 'url': url, 'is_published': True,
        })


class Migration(migrations.Migration):
    dependencies = [('journal', '0008_add_9233_students_and_lessons')]
    # Не удалять записи при откате: пользователь мог их изменить.
    operations = [migrations.RunPython(create_examples, migrations.RunPython.noop)]
