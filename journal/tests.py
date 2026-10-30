from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import time
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Grade, GradeChange, Lesson, LibraryResource, News, StudentProfile, StudyGroup, Subject


class PortalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(username='teacher', password='pass', role='teacher')
        self.other_teacher = User.objects.create_user(username='other', password='pass', role='teacher')
        self.student = User.objects.create_user(username='student', password='pass', role='student')
        self.group = StudyGroup.objects.create(name='A')
        self.other_group = StudyGroup.objects.create(name='B')
        self.profile = StudentProfile.objects.create(user=self.student, group=self.group)
        self.subject = Subject.objects.create(name='Математика')
        self.lesson = Lesson.objects.create(subject=self.subject, group=self.group, teacher=self.teacher, date=timezone.localdate())
        self.other_lesson = Lesson.objects.create(subject=self.subject, group=self.other_group, teacher=self.other_teacher, date=timezone.localdate())

    def test_only_published_news_and_resources_visible(self):
        News.objects.create(title='Публичная', content='Текст', is_published=True, published_at=timezone.now())
        hidden = News.objects.create(title='Черновик', content='Текст', is_published=False, published_at=timezone.now())
        News.objects.create(title='Будущая', content='Текст', is_published=True, published_at=timezone.now() + timedelta(days=1))
        LibraryResource.objects.create(title='Учебник', url='https://example.org', is_published=True)
        LibraryResource.objects.create(title='Скрытый материал', url='https://example.org', is_published=False)
        response = self.client.get(reverse('journal:news'))
        self.assertContains(response, 'Публичная')
        self.assertNotContains(response, 'Черновик')
        self.assertNotContains(response, 'Будущая')
        self.assertEqual(self.client.get(reverse('journal:news_detail', args=[hidden.pk])).status_code, 404)
        response = self.client.get(reverse('journal:library'))
        self.assertContains(response, 'Учебник')
        self.assertNotContains(response, 'Скрытый материал')

    def test_student_schedule_and_journal_access(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('journal:schedule'))
        self.assertContains(response, 'Математика')
        self.assertContains(response, 'teacher')
        self.assertNotContains(response, 'other')
        self.assertEqual(self.client.get(reverse('journal:group_journal', args=[self.other_group.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('journal:group_journal', args=[self.group.pk])).status_code, 200)

    def test_grade_permissions_and_validation(self):
        url = reverse('journal:add_grade', args=[self.lesson.pk, self.profile.pk])
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.post(url, {'value': '10'}).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(url, {'value': '101'}).status_code, 400)
        self.assertFalse(Grade.objects.exists())
        self.assertEqual(self.client.post(url, {'value': '10'}).status_code, 302)
        self.assertEqual(Grade.objects.get().value, 10)
        self.client.post(url, {'is_absent': 'on'})
        self.assertTrue(Grade.objects.get().is_absent)
        self.client.post(url, {'value': ''})
        self.assertFalse(Grade.objects.exists())
        wrong_group_url = reverse('journal:add_grade', args=[self.other_lesson.pk, self.profile.pk])
        self.assertEqual(self.client.post(wrong_group_url, {'value': '5'}).status_code, 404)

    def test_login_required(self):
        for name in ('schedule', 'profile', 'index'):
            self.assertEqual(self.client.get(reverse('journal:' + name)).status_code, 302)

    def test_grade_history_records_only_changes_and_survives_deletion(self):
        url = reverse('journal:add_grade', args=[self.lesson.pk, self.profile.pk])
        self.client.force_login(self.teacher)
        self.client.post(url, {'value': '10'})
        self.client.post(url, {'value': '010'})
        self.client.post(url, {'is_absent': 'on'})
        self.client.post(url, {'value': ''})
        changes = list(GradeChange.objects.order_by('pk').values_list('old_state', 'new_state'))
        self.assertEqual(changes, [('—', '10'), ('10', 'Н'), ('Н', '—')])
        self.lesson.delete()
        self.assertEqual(GradeChange.objects.count(), 3)

    def test_validation(self):
        self.lesson.start_time = time(12, 0)
        self.lesson.end_time = time(11, 0)
        with self.assertRaises(ValidationError):
            self.lesson.full_clean()
        wrong_grade = Grade(lesson=self.other_lesson, student=self.profile, value=10)
        with self.assertRaises(ValidationError):
            wrong_grade.full_clean()
        grade = Grade(lesson=self.lesson, student=self.profile, value=101)
        with self.assertRaises(ValidationError):
            grade.full_clean()
        with self.assertRaises(ValidationError):
            StudentProfile(user=self.other_teacher, group=self.group).full_clean()

    def test_admin_grades_are_read_only(self):
        admin = get_user_model().objects.create_superuser('root', 'root@example.com', 'pass')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('admin:journal_grade_add')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:journal_gradechange_add')).status_code, 403)

    def test_transfer_preserves_old_marks_and_records_admin_action(self):
        from .models import StudentTransfer
        admin = get_user_model().objects.create_superuser('root', 'root@example.com', 'pass', role='admin')
        self.client.force_login(self.teacher)
        self.client.post(reverse('journal:add_grade', args=[self.lesson.pk, self.profile.pk]), {'value': '17'})
        self.client.force_login(admin)
        url = reverse('admin:journal_studentprofile_change', args=[self.profile.pk])
        response = self.client.post(url, {'user': self.student.pk, 'group': self.other_group.pk, '_save': 'Сохранить'})
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.group, self.other_group)
        transfer = StudentTransfer.objects.get()
        self.assertEqual((transfer.old_group, transfer.new_group, transfer.actor), ('A', 'B', admin))
        response = self.client.get(reverse('journal:group_journal', args=[self.group.pk]))
        self.assertContains(response, '17')
        self.assertContains(response, 'Переведён(а)')
        self.assertNotContains(response, f'gradeModal{self.profile.pk}_{self.lesson.pk}')
        self.assertEqual(self.client.post(reverse('journal:add_grade', args=[self.lesson.pk, self.profile.pk]), {'value': '20'}).status_code, 404)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('journal:group_journal', args=[self.group.pk])).status_code, 403)

    def test_deleting_related_objects_with_grades_is_protected(self):
        from django.db.models import ProtectedError
        Grade.objects.create(lesson=self.lesson, student=self.profile, value=12)
        with self.assertRaises(ProtectedError):
            self.lesson.delete()
        with self.assertRaises(ProtectedError):
            self.profile.delete()
        self.lesson.group = self.other_group
        with self.assertRaises(ValidationError):
            self.lesson.full_clean()

    def test_demo_seed_is_explicit_and_refuses_duplicates(self):
        import os
        from unittest.mock import patch
        from django.core.management import call_command, CommandError
        from io import StringIO
        with patch.dict(os.environ, {'DEMO_PASSWORD': 'Demo1234!'}):
            with self.assertRaises(CommandError):
                call_command('seed_demo', stdout=StringIO())
            call_command('seed_demo', confirm_demo_database=True, stdout=StringIO())
            self.assertTrue(get_user_model().objects.get(username='demo_student').check_password('Demo1234!'))
            with self.assertRaises(CommandError):
                call_command('seed_demo', confirm_demo_database=True, stdout=StringIO())

    def test_csrf_protected_login_with_preview_cookie_settings(self):
        from django.test import Client, override_settings
        with override_settings(CSRF_COOKIE_SAMESITE='None', CSRF_COOKIE_SECURE=True,
                               SESSION_COOKIE_SAMESITE='None', SESSION_COOKIE_SECURE=True,
                               CSRF_TRUSTED_ORIGINS=['https://preview.example'], ALLOWED_HOSTS=['preview.example']):
            client = Client(enforce_csrf_checks=True)
            response = client.get(reverse('login'), secure=True, HTTP_HOST='preview.example')
            csrf = response.cookies['csrftoken']
            self.assertEqual(csrf['samesite'], 'None')
            self.assertTrue(csrf['secure'])
            response = client.post(reverse('login'), {'username': 'student', 'password': 'pass',
                'csrfmiddlewaretoken': csrf.value}, secure=True, HTTP_HOST='preview.example',
                HTTP_ORIGIN='https://preview.example')
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.cookies['sessionid']['secure'])
            self.assertEqual(response.cookies['sessionid']['samesite'], 'None')

    def test_preview_partitioned_cookies_and_csrf_failure_page(self):
        from django.test import Client, override_settings
        from django.conf import settings
        with override_settings(MIDDLEWARE=['config.preview_middleware.PartitionedPreviewCookies', *settings.MIDDLEWARE],
                               CSRF_FAILURE_VIEW='config.preview_views.csrf_failure',
                               CSRF_COOKIE_SECURE=True, CSRF_COOKIE_SAMESITE='None',
                               SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='None'):
            client = Client(enforce_csrf_checks=True)
            response = client.post(reverse('login'), {'username': 'student', 'password': 'pass'})
            self.assertEqual(response.status_code, 403)
            self.assertContains(response, 'Открыть вход в отдельной вкладке', status_code=403)
            response = client.get(reverse('login'))
            self.assertIn('; Partitioned', response.cookies['csrftoken'].OutputString())
            csrf = response.cookies['csrftoken'].value
            response = client.post(reverse('login'), {'username': 'student', 'password': 'pass', 'csrfmiddlewaretoken': csrf})
            self.assertEqual(response.status_code, 302)
            self.assertIn('; Partitioned', response.cookies['sessionid'].OutputString())
