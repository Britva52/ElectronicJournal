from django.db import models
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

    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Занятия"
        ordering = ['-date']  # Сортировка по дате (сначала новые)

    def __str__(self):
        return f"{self.subject.name} - {self.group.name} ({self.date})"


# 5. Оценка и посещаемость
class Grade(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="grades", verbose_name="Занятие")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="grades", verbose_name="Студент")

    # Мы убрали choices=MARKS. Теперь сюда можно записать любое положительное число!
    value = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Баллы / Оценка")
    is_absent = models.BooleanField(default=False, verbose_name="Отсутствовал (Н)")

    class Meta:
        verbose_name = "Оценка/Посещаемость"
        verbose_name_plural = "Оценки и Посещаемость"
        unique_together = ('lesson', 'student')

    def __str__(self):
        if self.is_absent:
            return f"{self.student.user} - Н ({self.lesson})"
        return f"{self.student.user} - {self.value} баллов ({self.lesson})"