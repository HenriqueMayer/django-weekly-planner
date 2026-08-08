"""View tests for the core app (PRD FR-01, FR-04)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class LandingViewTests(TestCase):
    def test_landing_loads_for_anonymous_user(self):
        response = self.client.get(reverse('core:landing'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/landing.html')
        content = response.content.decode()
        self.assertIn(reverse('accounts:signup'), content)
        self.assertIn(reverse('accounts:login'), content)

    def test_landing_shows_dashboard_link_for_authenticated_user(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('core:landing'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(reverse('core:dashboard'), content)


class DashboardViewTests(TestCase):
    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('/accounts/login/'))

    def test_dashboard_renders_grid_settings_and_colors_for_authenticated_user(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')
        self.assertIn('week_grid', response.context)
        self.assertIn('settings_form', response.context)
        self.assertIn('colors', response.context)
        self.assertIn('id="grid-table"', response.content.decode())
        self.assertContains(response, 'dark:bg-indigo-400')

    def test_htmx_week_navigation_returns_only_the_planner_surface(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(
            reverse('core:dashboard'),
            {'week': '2026-08-10'},
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'planner/partials/planner_surface.html')
        self.assertIn('id="planner-surface"', response.content.decode())
        self.assertNotIn('<html', response.content.decode())

    def test_htmx_month_navigation_returns_only_the_calendar_picker(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(
            reverse('core:dashboard'),
            {'week': '2026-08-03', 'month': '2026-09'},
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='calendar-picker',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'planner/partials/calendar_picker.html')
        content = response.content.decode()
        self.assertIn('id="calendar-picker"', content)
        self.assertNotIn('id="planner-surface"', content)
