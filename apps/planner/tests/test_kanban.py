"""Kanban presentation tests."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import TimeBlock

User = get_user_model()


class KanbanViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_selected_week_cards_are_grouped_by_existing_status(self):
        TimeBlock.objects.create(
            user=self.user, label='Done work', status='completed',
            scheduled_date=date(2026, 8, 3), day_of_week=0,
            start_time=time(9), end_time=time(10),
        )
        TimeBlock.objects.create(
            user=self.user, label='Other week', status='completed',
            scheduled_date=date(2026, 8, 10), day_of_week=0,
            start_time=time(9), end_time=time(10),
        )

        response = self.client.get(reverse('planner:kanban'), {'week': '2026-08-03'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Done work')
        self.assertNotContains(response, 'Other week')
