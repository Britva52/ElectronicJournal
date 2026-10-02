from django.contrib import admin
from .models import Subject, StudyGroup, StudentProfile, Lesson, Grade

# Простые модели регистрируем так:
admin.site.register(Subject)
admin.site.register(StudyGroup)

# Для профиля студента добавим поиск и фильтры
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'group')
    list_filter = ('group',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

# Для занятий
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('subject', 'group', 'teacher', 'date', 'topic')
    list_filter = ('subject', 'group', 'teacher', 'date')
    date_hierarchy = 'date'

# Для оценок
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'value', 'is_absent')
    list_filter = ('lesson__subject', 'lesson__group', 'is_absent')