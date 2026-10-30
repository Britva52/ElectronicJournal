from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


# 1. Предмет ("Математика", "Программирование")
class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название предмета")

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

    def __str__(self):
        return self.name


# 2. Учебная группа ("ИВТ-21", "10-А")
class StudyGroup(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Название группы")

    class Meta:
        verbose_name = "Учебная группа"
        verbose_name_plural = "Учебные группы"

    def __str__(self):
        return self.name


# 3. Профиль студента (Связывает пользователя-студента с его группой)
class StudentProfile(models.Model):
    # Связь "один к одному" модели с пользователем
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Студент")
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="students", verbose_name="Группа")

    def clean(self):
        super().clean()
        if self.pk and self.grades.exists():
            original = StudentProfile.objects.filter(pk=self.pk).values('user_id').first()
            if original and original['user_id'] != self.user_id:
                raise ValidationError({"user": "Нельзя заменить пользователя профиля, содержащего оценки."})
        if self.user_id and self.user.role != "student":
            raise ValidationError({"user": "Профиль можно создать только для пользователя с ролью студента."})

    class Meta:
        verbose_name = "Профиль студента"
        verbose_name_plural = "Профили студентов"

    def __str__(self):
        return f"{self.user} ({self.group.name})"


# 4. Занятие (Урок)
class Lesson(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Предмет")
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, verbose_name="Группа")
    # Преподаватель (у кого роль "teacher")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        verbose_name="Преподаватель"
    )
    date = models.DateField(verbose_name="Дата занятия")
    topic = models.CharField(max_length=255, blank=True, verbose_name="Тема занятия")
    start_time = models.TimeField("Время начала", null=True, blank=True)
    end_time = models.TimeField("Время окончания", null=True, blank=True)
    room = models.CharField("Аудитория", max_length=100, blank=True)

    def clean(self):
        super().clean()
        if self.pk and self.grades.exists():
            original = Lesson.objects.filter(pk=self.pk).values('group_id').first()
            if original and original['group_id'] != self.group_id:
                raise ValidationError({"group": "Нельзя изменить группу занятия с оценками."})
        if self.teacher_id and self.teacher.role != "teacher":
            raise ValidationError({"teacher": "Укажите пользователя с ролью преподавателя."})
        if self.end_time and not self.start_time:
            raise ValidationError({"start_time": "Укажите время начала занятия."})
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Время окончания должно быть позже времени начала."})

    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Занятия"
        ordering = ['-date']  # Сортировка по дате (сначала новые)

    def __str__(self):
        return f"{self.subject.name} - {self.group.name} ({self.date})"


# 5. Оценка и посещаемость
class Grade(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name="grades", verbose_name="Занятие")
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="grades", verbose_name="Студент")

    value = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Баллы / Оценка")
    is_absent = models.BooleanField(default=False, verbose_name="Отсутствовал (Н)")

    def clean(self):
        super().clean()
        errors = {}
        if self.lesson_id and self.student_id and self.lesson.group_id != self.student.group_id:
            errors["student"] = "Студент должен состоять в группе занятия."
        if self.value is not None and not 1 <= self.value <= 100:
            errors["value"] = "Укажите балл от 1 до 100."
        if self.is_absent and self.value is not None:
            errors["value"] = "Нельзя одновременно указать балл и отсутствие."
        if not self.is_absent and self.value is None:
            errors["value"] = "Укажите балл или отметьте отсутствие."
        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Оценка/Посещаемость"
        verbose_name_plural = "Оценки и Посещаемость"
        unique_together = ('lesson', 'student')

    def __str__(self):
        if self.is_absent:
            return f"{self.student.user} - Н ({self.lesson})"
        return f"{self.student.user} - {self.value} баллов ({self.lesson})"

class News(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    content = models.TextField('Текст')
    published_at = models.DateTimeField('Дата публикации')
    is_published = models.BooleanField('Опубликовано', default=False)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-published_at', '-pk']

    def __str__(self):
        return self.title


class LibraryResource(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    subject = models.ForeignKey(Subject, verbose_name='Предмет', null=True, blank=True, on_delete=models.SET_NULL)
    url = models.URLField('Ссылка на материал')
    is_published = models.BooleanField('Опубликовано', default=False)

    class Meta:
        verbose_name = 'Материал библиотеки'
        verbose_name_plural = 'Материалы библиотеки'
        ordering = ['title', 'pk']

    def __str__(self):
        return self.title


class GradeChange(models.Model):
    """История изменений через интерфейс журнала; снимки сохраняются при удалении объектов."""
    created_at = models.DateTimeField("Время изменения", auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, verbose_name="Автор")
    actor_name = models.CharField("Логин автора", max_length=150)
    student_name = models.CharField("Студент", max_length=255)
    lesson_description = models.CharField("Занятие", max_length=255)
    old_state = models.CharField("Было", max_length=30)
    new_state = models.CharField("Стало", max_length=30)

    class Meta:
        verbose_name = "Изменение оценки"
        verbose_name_plural = "История изменений оценок"
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.student_name}: {self.old_state} → {self.new_state}"


class StudentTransfer(models.Model):
    created_at = models.DateTimeField("Время перевода", auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, verbose_name="Автор")
    actor_name = models.CharField("Логин автора", max_length=150)
    student = models.ForeignKey(StudentProfile, null=True, on_delete=models.SET_NULL, verbose_name="Профиль")
    student_name = models.CharField("Логин студента", max_length=150)
    old_group = models.CharField("Из группы", max_length=20)
    new_group = models.CharField("В группу", max_length=20)

    class Meta:
        verbose_name = "Перевод студента"
        verbose_name_plural = "История переводов студентов"
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return f"{self.student_name}: {self.old_group} → {self.new_group}"
