from datetime import date, time
from random import Random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from journal.models import Grade, Lesson, ScheduleClosure, StudentProfile, StudyGroup, Subject


class Command(BaseCommand):
    help = 'Заполнить отдельную учебную базу данными для проверки журнала.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, 'ALLOW_EXAMPLE_SCHEDULE', False):
            raise CommandError('Команда доступна только для отдельной базы --settings=config.demo.')
        group = StudyGroup.objects.get(name='о-П-923/3')
        users = get_user_model()
        teachers = {
            'math': ('draft_teacher_radinskaya', 'Радинская Л. В.'),
            'language': ('draft_teacher_language', 'Кириченко Н. Д. / Чернышева Ю. А.'),
            'tech': ('draft_teacher_radinskiy', 'Радинский А. Е.'),
            'docs': ('draft_teacher_gladkih', 'Гладких Ю. П.'),
            'security': ('draft_teacher_semenov', 'Семёнов Р. В.'),
            'pe': ('draft_teacher_physical', 'Преподаватель физкультуры не указан'),
        }
        rows = [
            (2, '10:10', '11:40', '02.03 Математическое моделирование', 'math', '311'),
            (2, '12:10', '13:40', 'Собрание группы', 'math', '216, 2-й корпус'),
            (2, '13:50', '15:20', 'Иностранный язык в профессиональной деятельности', 'language', '102, 219, 2-й корпус'),
            (2, '15:40', '17:10', 'Физическая культура', 'pe', ''),
            (3, '13:50', '15:20', 'Численные методы', 'math', '311'),
            (3, '15:40', '17:10', '02.03 Математическое моделирование', 'math', '311'),
            (5, '12:10', '13:40', '11.01 Технология разработки и защиты баз данных', 'tech', '206, 2-й корпус'),
            (5, '13:50', '15:20', '02.02 Инструментальные средства разработки программного обеспечения', 'tech', '206, 2-й корпус'),
            (5, '15:40', '17:10', 'Стандартизация, сертификация и техническое документоведение', 'docs', '311'),
            (5, '17:20', '18:50', 'Стандартизация, сертификация и техническое документоведение', 'docs', '311'),
            (6, '15:40', '17:10', '11.01 Технология разработки и защиты баз данных', 'tech', '206, 2-й корпус'),
            (6, '17:20', '18:50', '02.02 Инструментальные средства разработки программного обеспечения', 'tech', '206, 2-й корпус'),
            (7, '13:40', '15:00', 'Численные методы', 'math', '311'),
            (7, '15:10', '16:30', 'Информационная безопасность', 'security', '212, 2-й корпус'),
        ]
        ScheduleClosure.objects.get_or_create(group=group, date=date(2026, 11, 4), defaults={'reason': 'Праздничный день'})
        # меняем только исходные заготовки без оценок
        original = {
            (2, '10:10'): ('10:10', '11:40', '311', ''),
            (2, '12:10'): ('12:10', '13:40', '218, 2-й корпус', ''),
            (2, '13:50'): ('13:50', '15:20', '208, 1-й корпус; 103', 'Две подгруппы; уточните свою.'),
            (2, '15:40'): ('15:40', '17:10', '', 'Время и место необходимо уточнить по расписанию физкультуры.'),
            (3, '13:50'): ('13:50', '15:20', '311', ''), (3, '15:40'): ('15:40', '17:10', '311', ''),
            (5, '12:10'): ('12:10', '13:40', '208, 2-й корпус', ''), (5, '13:50'): ('13:50', '15:20', '208, 2-й корпус', ''),
            (5, '15:40'): ('15:40', '17:10', '311', ''), (5, '17:20'): ('17:20', '18:50', '311', ''),
            (6, '15:40'): ('15:40', '17:10', '208, 2-й корпус', ''), (6, '17:20'): ('17:20', '18:50', '208, 2-й корпус', ''),
            (7, '13:40'): ('13:50', '15:20', '311', ''), (7, '15:10'): ('15:30', '16:30', '212, 2-й корпус', ''),
        }
        old_topic = 'По скриншоту: дата и актуальность требуют проверки.'
        created_lessons = updated_lessons = skipped = 0
        for day, start, end, title, teacher_key, room in rows:
            lesson_date = date(2026, 11, day)
            start_time = time.fromisoformat(start)
            username, name = teachers[teacher_key]
            old_start, old_end, old_room, note = original[(day, start)]
            original_topic = old_topic + (f' {note}' if note else '')
            original_lesson = Lesson.objects.filter(group=group, date=lesson_date,
                start_time=time.fromisoformat(old_start), end_time=time.fromisoformat(old_end), room=old_room,
                subject__name=title, teacher__username=username, teacher__first_name=name,
                teacher__role='teacher', topic=original_topic, grades__isnull=True).first()
            if original_lesson and not Lesson.objects.filter(group=group, date=lesson_date, start_time=start_time).exclude(pk=original_lesson.pk).exists():
                original_lesson.start_time = start_time
                original_lesson.end_time = time.fromisoformat(end)
                original_lesson.room = room
                original_lesson.topic = 'Учебная база: данные со скриншота; дату и время необходимо подтвердить.'
                if day == 3:
                    original_lesson.topic += ' В объявлении указано сокращённое расписание; время требуется уточнить.'
                original_lesson.save(update_fields=['start_time', 'end_time', 'room', 'topic'])
                updated_lessons += 1
                continue
            # занятые слоты и оценки не перезаписываем
            if Lesson.objects.filter(group=group, date=lesson_date, start_time__in=[start_time, time.fromisoformat(old_start)]).exists():
                skipped += 1
                continue
            teacher, created = users.objects.get_or_create(username=username, defaults={
                'first_name': name, 'role': 'teacher', 'password': '!', 'is_active': True,
            })
            if not created and (teacher.role != 'teacher' or teacher.first_name != name):
                skipped += 1
                continue
            subject = Subject.objects.filter(name=title).order_by('pk').first()
            if not subject:
                subject = Subject.objects.create(name=title)
            topic = 'Учебная база: данные со скриншота; дату и время необходимо подтвердить.'
            if day == 3:
                topic += ' В объявлении указано сокращённое расписание; время требуется уточнить.'
            Lesson.objects.create(group=group, subject=subject, teacher=teacher, date=lesson_date,
                                  start_time=start_time, end_time=time.fromisoformat(end), room=room, topic=topic)
            created_lessons += 1

        # лишнюю исходную пару удаляем только если её никто не менял
        Lesson.objects.filter(group=group, date=date(2026, 11, 7), start_time=time(16, 40), end_time=time(18, 0),
            subject__name='Информационная безопасность', room='212, 2-й корпус',
            teacher__username='draft_teacher_semenov', teacher__first_name='Семёнов Р. В.',
            topic=old_topic, grades__isnull=True).delete()

        # случайные баллы только для заготовок и только за прошедшие занятия
        students = StudentProfile.objects.filter(group=group, user__username__startswith='draft_9233_').order_by('user__username')
        lessons = Lesson.objects.filter(group=group, date__gte=date(2026, 11, 2), date__lte=date(2026, 11, 3),
                    teacher__username__startswith='draft_teacher_').exclude(subject__name__in=['Собрание группы', 'Физическая культура']).order_by('date', 'start_time', 'pk')
        random = Random(9233)
        created_grades = 0
        for student in students:
            for lesson in lessons:
                # не трогаем занятия, которые пользователь успел изменить
                if not (lesson.topic.startswith('По скриншоту: дата и актуальность требуют проверки.') or lesson.topic.startswith('Учебная база: данные со скриншота')):
                    continue
                _, created = Grade.objects.get_or_create(student=student, lesson=lesson, defaults={'value': random.randint(60, 100)})
                created_grades += int(created)
        self.stdout.write(self.style.SUCCESS(f'Добавлено занятий: {created_lessons}, обновлено исходных заготовок: {updated_lessons}, отметок: {created_grades}; пропущено: {skipped}.'))
        self.stdout.write('Учебные баллы случайные, изменённые занятия и оценки сохранены. Проверьте время 3 ноября по объявлению.')
