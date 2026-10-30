from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.db import transaction
from .models import Subject, StudyGroup, StudentProfile, Lesson, Grade, GradeChange, StudentTransfer, News, LibraryResource

admin.site.register(Subject)
admin.site.register(StudyGroup)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'group')
    list_filter = ('group',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    def save_model(self, request, obj, form, change):
        # Стандартная форма Django admin сохраняется в транзакции; фиксируем и перевод.
        with transaction.atomic():
            old = StudentProfile.objects.select_for_update().select_related('group').filter(pk=obj.pk).first() if change else None
            super().save_model(request, obj, form, change)
            if old and old.group_id != obj.group_id:
                StudentTransfer.objects.create(actor=request.user, actor_name=request.user.username,
                    student=obj, student_name=obj.user.username, old_group=old.group.name, new_group=obj.group.name)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'subject', 'group', 'teacher', 'room', 'topic')
    list_filter = ('subject', 'group', 'teacher', 'date')
    search_fields = ('subject__name', 'group__name', 'teacher__username', 'teacher__last_name', 'topic', 'room')
    date_hierarchy = 'date'


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    # Все изменения должны проходить через журнал, чтобы сохранялась история.
    list_display = ('student', 'lesson', 'value', 'is_absent')
    list_filter = ('lesson__subject', 'lesson__group', 'is_absent')
    readonly_fields = ('student', 'lesson', 'value', 'is_absent')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GradeChange)
class GradeChangeAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor_name', 'student_name', 'lesson_description', 'old_state', 'new_state')
    search_fields = ('actor_name', 'student_name', 'lesson_description')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'actor', 'actor_name', 'student_name', 'lesson_description', 'old_state', 'new_state')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')


@admin.register(LibraryResource)
class LibraryResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'is_published')
    list_filter = ('subject', 'is_published')
    search_fields = ('title', 'description')


@admin.register(StudentTransfer)
class StudentTransferAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'student_name', 'old_group', 'new_group', 'actor_name')
    search_fields = ('student_name', 'old_group', 'new_group', 'actor_name')
    readonly_fields = ('created_at', 'student', 'student_name', 'old_group', 'new_group', 'actor', 'actor_name')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class AdminLogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag')
    list_filter = ('action_flag', 'content_type', 'action_time')
    search_fields = ('object_repr', 'user__username')
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
