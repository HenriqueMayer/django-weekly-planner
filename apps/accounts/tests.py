"""View tests for the accounts app (native Django authentication, PRD
FR-02/FR-03)."""

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import PlannerSettings

User = get_user_model()


class SignUpViewTests(TestCase):
    def test_signup_creates_user_logs_in_and_redirects_to_dashboard(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'alice',
            'password1': 'a-very-strong-pass123',
            'password2': 'a-very-strong-pass123',
        })

        self.assertRedirects(response, reverse('core:dashboard'))
        user = User.objects.get(username='alice')
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)
        # The post_save signal (PRD 8.1.4) must have already fired.
        self.assertTrue(PlannerSettings.objects.filter(user=user).exists())

    def test_signup_invalid_shows_inline_errors_and_does_not_create_user(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'alice',
            'password1': 'a-very-strong-pass123',
            'password2': 'does-not-match',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'didn’t match', status_code=200)
        self.assertFalse(User.objects.filter(username='alice').exists())


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='correct-pass123')

    def test_login_success_redirects_and_authenticates(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'alice', 'password': 'correct-pass123',
        })

        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_wrong_password_shows_error_and_does_not_authenticate(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'alice', 'password': 'wrong-password',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct', status_code=200)
        self.assertNotIn(SESSION_KEY, self.client.session)


class LogoutViewTests(TestCase):
    def test_logout_clears_session_and_dashboard_then_requires_login_again(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(user)

        response = self.client.post(reverse('accounts:logout'))

        self.assertRedirects(response, reverse('core:landing'))
        self.assertNotIn(SESSION_KEY, self.client.session)

        dashboard_response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dashboard_response.status_code, 302)
        self.assertTrue(dashboard_response['Location'].startswith('/accounts/login/'))
