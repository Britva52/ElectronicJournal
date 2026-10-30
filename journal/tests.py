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

    def test_week_schedule_navigation_and_group_permissions(self):
        from datetime import timedelta
        admin = get_user_model().objects.create_user(username='schedule_admin', role='admin', password='pass')
        self.client.force_login(admin)
        url = reverse('journal:schedule')
        response = self.client.get(url, {'group': self.group.pk, 'week': self.lesson.date.isoformat()})
        self.assertContains(response, 'Математика')
        self.assertContains(response, 'Понедельник')
        self.assertNotContains(response, 'other')
        self.assertEqual(self.client.get(url, {'week': 'не-дата'}).status_code, 400)
        self.assertEqual(self.client.get(url, {'group': 'не-группа'}).status_code, 400)
        next_week = self.lesson.date + timedelta(days=7)
        self.assertNotContains(self.client.get(url, {'week': next_week.isoformat()}), 'Математика')
        self.client.force_login(self.student)
        response = self.client.get(url, {'group': self.other_group.pk})
        self.assertContains(response, 'other')
        self.assertEqual(self.client.get(reverse('journal:group_journal', args=[self.other_group.pk])).status_code, 403)

    def test_example_schedule_is_isolated_and_idempotent(self):
        import os
        from io import StringIO
        from unittest.mock import patch
        from django.test import override_settings
        from django.core.management import call_command, CommandError
        with patch.dict(os.environ, {'DEMO_PASSWORD': 'Demo2026!'}):
            with self.assertRaises(CommandError):
                call_command('seed_example_schedule', stdout=StringIO())
            with override_settings(ALLOW_EXAMPLE_SCHEDULE=True):
                call_command('seed_example_schedule', week='2026-10-26', stdout=StringIO())
                self.assertTrue(StudyGroup.objects.filter(name='о-П-923/3').exists())
                self.assertTrue(StudyGroup.objects.filter(name='о-Э-923/3').exists())
                user = get_user_model().objects.get(username='demo_923_student')
                self.assertTrue(user.check_password('Demo2026!'))
                self.client.force_login(user)
                response = self.client.get(reverse('journal:schedule'), {'week': '2026-10-26'})
                self.assertContains(response, 'Математическое моделирование')
                self.assertContains(response, '10:10')
                self.assertContains(response, 'о-П-1124')
                self.assertEqual(len(response.context['days'][0]['lessons']), 4)
                total = Lesson.objects.count()
                call_command('seed_example_schedule', week='2026-10-26', stdout=StringIO())
                self.assertEqual(Lesson.objects.count(), total)
                call_command('seed_example_schedule', week='2026-11-02', stdout=StringIO())
                self.assertGreater(Lesson.objects.count(), total)

    def test_empty_week_links_to_existing_week_and_preserves_group_filter(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('journal:schedule'), {
            'group': self.other_group.pk, 'week': (self.other_lesson.date + timedelta(days=14)).isoformat(),
        })
        self.assertContains(response, 'Перейти к ближайшей неделе с занятиями')
        self.assertContains(response, f'group={self.other_group.pk}')
        self.assertEqual(self.client.get(reverse('journal:schedule'), {'group': self.other_group.pk}).status_code, 200)
        self.assertEqual(self.client.get(reverse('journal:group_journal', args=[self.other_group.pk])).status_code, 403)

    def test_classic_journal_shows_edit_control_only_for_authorized_teacher(self):
        Grade.objects.create(lesson=self.lesson, student=self.profile, value=85)
        url = reverse('journal:group_journal', args=[self.group.pk])
        self.client.force_login(self.teacher)
        response = self.client.get(url)
        self.assertContains(response, '85')
        self.assertContains(response, f'gradeModal{self.profile.pk}_{self.lesson.pk}')
        self.assertContains(response, reverse('journal:add_grade', args=[self.lesson.pk, self.profile.pk]))
        self.client.force_login(self.student)
        response = self.client.get(url)
        self.assertContains(response, '85')
        self.assertNotContains(response, f'gradeModal{self.profile.pk}_{self.lesson.pk}')

    def test_groups_and_screenshot_reference_are_available(self):
        from .models import ScheduleReference
        group = StudyGroup.objects.get(name='о-П-923/3')
        for name in ['о-П-923/1', 'о-П-923/2', 'о-Э-923/1', 'о-Э-923/2', 'о-Э-923/3', 'о-П-1124', 'о-П-924/1']:
            self.assertTrue(StudyGroup.objects.filter(name=name).exists())
        self.assertEqual(ScheduleReference.objects.filter(group=group).count(), 18)
        self.assertEqual(Lesson.objects.filter(group=group).count(), 18)
        self.client.force_login(self.student)
        url = reverse('journal:schedule')
        response = self.client.get(url, {'group': group.pk})
        self.assertContains(response, 'дата и актуальность требуют проверки')
        response = self.client.get(url, {'group': group.pk, 'reference': '1'})
        self.assertContains(response, 'Образец по вашему скриншоту')
        self.assertContains(response, 'Математическое моделирование')
        self.assertContains(response, 'Радинская Л. В.')
        self.assertContains(response, 'Информационная безопасность')
        self.assertContains(response, '16:40')
        Lesson.objects.create(group=group, date=timezone.localdate(), subject=self.subject, teacher=self.teacher)
        response = self.client.get(url, {'group': group.pk})
        self.assertNotContains(response, 'Образец по вашему скриншоту')
        self.assertContains(response, 'Посмотреть образец со скриншота')
        response = self.client.get(url, {'group': group.pk, 'reference': '1'})
        self.assertContains(response, 'Образец по вашему скриншоту')
        self.assertEqual(self.client.get(reverse('journal:group_journal', args=[group.pk])).status_code, 403)

    def test_migrated_students_are_placeholders_and_admin_can_manage_journal(self):
        group = StudyGroup.objects.get(name='о-П-923/3')
        names = set(StudentProfile.objects.filter(group=group).values_list('user__first_name', flat=True))
        self.assertTrue({'Артур', 'Егор', 'Денис', 'Лёша', 'Максим', 'Тимофей', 'Мирон'} <= names)
        self.assertTrue(all(not p.user.has_usable_password() for p in StudentProfile.objects.filter(group=group).select_related('user')))
        self.assertTrue(Lesson.objects.filter(group=group, topic__contains='актуальность требуют проверки').exists())
        root = get_user_model().objects.create_superuser('test_admin', 'a@example.com', 'pass', role='student')
        self.client.force_login(root)
        self.assertContains(self.client.get(reverse('journal:index')), 'о-П-923/3')
        lesson = Lesson.objects.filter(group=group).first()
        student = StudentProfile.objects.filter(group=group).first()
        self.assertEqual(self.client.post(reverse('journal:add_grade', args=[lesson.pk, student.pk]), {'value': '77'}).status_code, 302)
        self.assertEqual(Grade.objects.get(lesson=lesson, student=student).value, 77)

    def test_news_search_only_public_and_demo_content_visible(self):
        public = News.objects.create(title='Уникальный открытый материал', content='Содержимое', is_published=True, published_at=timezone.now())
        private = News.objects.create(title='Уникальный черновик', content='Содержимое', is_published=False, published_at=timezone.now())
        response = self.client.get(reverse('journal:news'), {'q': 'Уникальный'})
        self.assertContains(response, public.title)
        self.assertNotContains(response, private.title)
        self.assertContains(self.client.get(reverse('journal:news')), '[Пример]')
        self.assertEqual(self.client.get(reverse('journal:news_detail', args=[private.pk])).status_code, 404)
        self.assertContains(self.client.get(reverse('journal:news_detail', args=[public.pk])), public.content)

    def test_library_filters_search_and_pagination(self):
        subject = Subject.objects.create(name='Тестирование систем')
        other_subject = Subject.objects.create(name='Скрытый предмет')
        for i in range(13):
            LibraryResource.objects.create(title=f'Учебный материал {i:02}', description='особая метка', subject=subject, url='https://example.org', is_published=True)
        LibraryResource.objects.create(title='Секретный', description='особая метка', subject=other_subject, url='https://example.org', is_published=False)
        url = reverse('journal:library')
        response = self.client.get(url, {'q': 'особая метка', 'subject': subject.pk})
        self.assertEqual(response.context['page'].paginator.count, 13)
        self.assertNotContains(response, 'Секретный')
        self.assertNotContains(response, 'Скрытый предмет')
        self.assertContains(response, 'subject=')
        self.assertContains(response, 'page=2')
        self.assertEqual(self.client.get(url, {'subject': 'bad'}).status_code, 400)
        response = self.client.get(url, {'q': 'особая метка', 'subject': subject.pk, 'page': 2})
        self.assertEqual(len(response.context['page'].object_list), 1)
        self.assertContains(response, 'Сбросить')

    def test_profile_edit_contact_is_limited_to_current_user(self):
        url = reverse('journal:profile_edit')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.student)
        response = self.client.post(url, {'email': 'bad-email', 'role': 'admin'})
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, 'student')
        response = self.client.post(url, {'email': 'student@example.org', 'role': 'admin', 'is_superuser': 'on'})
        self.assertRedirects(response, reverse('journal:profile'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, 'student@example.org')
        self.assertEqual(self.student.role, 'student')
        self.assertFalse(self.student.is_superuser)
        self.assertContains(self.client.get(reverse('journal:profile')), 'student@example.org')
