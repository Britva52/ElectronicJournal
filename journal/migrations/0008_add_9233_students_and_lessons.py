from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.utils import timezone


def add_students_and_lessons(apps, schema_editor):
    db = schema_editor.connection.alias
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)
    Group = apps.get_model('journal', 'StudyGroup')
    Profile = apps.get_model('journal', 'StudentProfile')
    Reference = apps.get_model('journal', 'ScheduleReference')
    Subject = apps.get_model('journal', 'Subject')
    Lesson = apps.get_model('journal', 'Lesson')
    group, _ = Group.objects.using(db).get_or_create(name='о-П-923/3')

    # Заготовки без пароля. Уже существующих пользователей и их профили не меняем.
    names = [('artur', 'Артур'), ('egor', 'Егор'), ('denis', 'Денис'),
             ('lesha', 'Лёша'), ('maksim', 'Максим'), ('timofey', 'Тимофей'), ('miron', 'Мирон')]
    for slug, name in names:
        if Profile.objects.using(db).filter(group=group, user__role='student').filter(
            user__first_name=name
        ).exists() or Profile.objects.using(db).filter(group=group, user__role='student', user__username=name).exists():
            continue
        username = f'draft_9233_{slug}'
        user, created = User.objects.using(db).get_or_create(username=username, defaults={
            'first_name': name, 'role': 'student', 'password': '!', 'is_active': True,
        })
        if created:
            Profile.objects.using(db).create(user=user, group=group)

    # Скриншот не содержит подтверждённых дат: создаём одну неделю на момент
    # миграции с явной пометкой. Существующие занятия в тех же слотах не меняем.
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    teachers = {
        'Радинская Л. В.': ('draft_teacher_radinskaya', 'Радинская Л. В.'),
        'Кириченко Н. Д. / Чернышева Ю. А.': ('draft_teacher_language', 'Кириченко Н. Д. / Чернышева Ю. А.'),
        'Донская Н. А.': ('draft_teacher_donskaya', 'Донская Н. А.'),
        'Радинский А. Е.': ('draft_teacher_radinskiy', 'Радинский А. Е.'),
        'Гладких Ю. П.': ('draft_teacher_gladkih', 'Гладких Ю. П.'),
        'Семёнов Р. В.': ('draft_teacher_semenov', 'Семёнов Р. В.'),
        '': ('draft_teacher_physical', 'Преподаватель физкультуры не указан'),
    }
    for ref in Reference.objects.using(db).filter(group=group).order_by('weekday', 'number'):
        if ref.weekday > 6 or len(ref.subject) > 100:
            continue
        day = monday + timedelta(days=ref.weekday)
        if Lesson.objects.using(db).filter(group=group, date=day, start_time=ref.start_time).exists():
            continue
        username, display_name = teachers.get(ref.teacher, ('draft_teacher_other', 'Преподаватель не подтверждён'))
        teacher, created = User.objects.using(db).get_or_create(username=username, defaults={
            'first_name': display_name, 'role': 'teacher', 'password': '!', 'is_active': True,
        })
        # При конфликте имён не присваиваем занятие посторонней учётной записи.
        if not created and (teacher.role != 'teacher' or teacher.first_name != display_name):
            continue
        subject = Subject.objects.using(db).filter(name=ref.subject).order_by('pk').first()
        if subject is None:
            subject = Subject.objects.using(db).create(name=ref.subject)
        Lesson.objects.using(db).create(group=group, subject=subject, teacher=teacher, date=day,
            start_time=ref.start_time, end_time=ref.end_time, room=ref.room,
            topic='По скриншоту: дата и актуальность требуют проверки.' + (f' {ref.note}' if ref.note else ''))


class Migration(migrations.Migration):
    dependencies = [('journal', '0007_groups_and_schedule_reference'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.RunPython(add_students_and_lessons, migrations.RunPython.noop)]
