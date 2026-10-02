from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Добавляем наше поле "role" при редактировании пользователя
    fieldsets = UserAdmin.fieldsets + (
        (
            "Дополнительная информация",
            {
                "fields": ("role",),
            },
        ),
    )

    # Добавляем наше поле "role" при создании нового пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Дополнительная информация",
            {
                "fields": ("role",),
            },
        ),
    )