from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations


def add_content(apps, schema_editor):
    db = schema_editor.connection.alias
    News = apps.get_model('journal', 'News')
    Resource = apps.get_model('journal', 'LibraryResource')

    # убираем только нетронутые стандартные записи
    old_news = [
        ('[Пример] Добро пожаловать на учебный портал', 'Это пример публикации для курсового проекта. В этом разделе администратор сможет размещать новости, объявления и важную информацию для студентов и преподавателей.'),
        ('[Пример] Как пользоваться электронным журналом', 'Откройте раздел «Электронный журнал», выберите группу и просмотрите оценки по занятиям. Преподаватель может внести отметку на своём занятии, а администратор — управлять данными через админ-панель.'),
        ('[Пример] Где найти расписание', 'В разделе «Расписание» можно выбрать учебную группу и перейти к нужной неделе. Даты и изменения занятий следует уточнять в учебной части.'),
        ('[Пример] Учебные материалы в библиотеке', 'В библиотеке собраны ссылки на материалы для самостоятельной работы. Используйте поиск или фильтр по предмету. Администратор может добавлять и скрывать материалы через админ-панель.'),
    ]
    for title, content in old_news:
        News.objects.using(db).filter(title=title, content=content).update(is_published=False)

    old_resources = [
        ('[Пример] Python: официальная документация', 'https://docs.python.org/3/', 'Справочник языка Python и учебное руководство.'),
        ('[Пример] Django: документация', 'https://docs.djangoproject.com/', 'Руководства по созданию веб-приложений на Django.'),
        ('[Пример] PostgreSQL: введение в SQL', 'https://www.postgresql.org/docs/current/tutorial-sql.html', 'Основы работы с реляционными базами данных и SQL.'),
        ('[Пример] MDN: веб-технологии', 'https://developer.mozilla.org/ru/', 'Справочные материалы по HTML, CSS и JavaScript.'),
        ('[Пример] Git: руководство', 'https://git-scm.com/book/ru/v2', 'Официальная книга по системе контроля версий Git.'),
    ]
    for title, url, description in old_resources:
        Resource.objects.using(db).filter(title=title, url=url, description=description).update(is_published=False)

    # дата публикации условная: на баннерах она не указана
    moscow = ZoneInfo('Europe/Moscow')
    entries = [
        ('4 ноября — выходной день', '4 ноября — выходной день. 3 ноября, в канун праздника, занятия проводятся в сокращённом формате. Время занятий указано на баннере.\n\nИнформация перенесена с предоставленного объявления; дату его публикации необходимо уточнить.', 'journal/news/holiday.png', datetime(2026, 11, 2, 12, tzinfo=moscow)),
        ('Посвящение в студенты: созвездие талантов', 'Посвящение в студенты состоится 6 ноября 2026 года, в пятницу. Встреча гостей — в 13:00, начало — в 14:00. Место: «Место встречи Звёздный», проспект Вернадского, 14, Москва.\n\nИнформация перенесена с предоставленного объявления; дату его публикации необходимо уточнить.', 'journal/news/dedication.png', datetime(2026, 11, 2, 11, tzinfo=moscow)),
        ('Дополнительные задания по дисциплинам', 'С 26 октября по 7 ноября 2026 года в ЭИОС по дисциплинам и междисциплинарным курсам будут размещены дополнительные задания с указанием сроков выполнения.\n\nИнформация перенесена с предоставленного объявления; дату его публикации необходимо уточнить.', 'journal/news/assignments.png', datetime(2026, 10, 25, 12, tzinfo=moscow)),
        ('Текущий контроль по дисциплинам', 'С 7 по 13 октября 2026 года в колледже проводится текущий контроль: контрольные работы по всем дисциплинам. Согласно объявлению, явка обязательна.\n\nИнформация перенесена с предоставленного объявления; дату его публикации необходимо уточнить.', 'journal/news/assessment.png', datetime(2026, 10, 6, 12, tzinfo=moscow)),
    ]
    for title, content, banner, published_at in entries:
        if not News.objects.using(db).filter(title=title).exists():
            News.objects.using(db).create(title=title, content=content, banner=banner, published_at=published_at, is_published=True)

    for title, url, description in [
        ('ibooks.ru', 'https://ibooks.ru/', 'Электронно-библиотечная система. Условия доступа уточняйте в библиотеке колледжа.'),
        ('Юрайт', 'https://urait.ru/', 'Образовательная платформа. Условия доступа уточняйте в библиотеке колледжа.'),
    ]:
        if not Resource.objects.using(db).filter(url=url).exists():
            Resource.objects.using(db).create(title=title, url=url, description=description, is_published=True)


class Migration(migrations.Migration):
    dependencies = [('journal', '0010_news_banner')]
    operations = [migrations.RunPython(add_content, migrations.RunPython.noop)]
