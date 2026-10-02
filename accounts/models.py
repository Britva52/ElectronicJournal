from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        TEACHER = "teacher", "Преподаватель"
        STUDENT = "student", "Студент"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="Роль",
    )

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return full_name
        return self.username