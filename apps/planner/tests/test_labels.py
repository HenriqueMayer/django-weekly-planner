"""Card label creation, association, and ownership tests."""

from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import ActivityEvent, CardLabel, TimeBlock

User = get_user_model()


class LabelViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.block = TimeBlock.objects.create(
            user=self.user, label='Project', day_of_week=0,
            start_time=time(9), end_time=time(10),
        )
        self.client.force_login(self.user)

    def test_add_and_remove_label(self):
        response = self.client.post(
            reverse('planner:label-add', args=[self.block.pk]),
            {'name': 'Urgent', 'hex_code': '#EF4444'},
        )
        self.assertEqual(response.status_code, 200)
        label = CardLabel.objects.get(user=self.user, name='Urgent')
        self.assertTrue(self.block.labels.filter(pk=label.pk).exists())
        self.assertTrue(ActivityEvent.objects.filter(event_type='label_added').exists())

        response = self.client.post(
            reverse('planner:label-remove', args=[self.block.pk, label.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.block.labels.filter(pk=label.pk).exists())
        self.assertTrue(ActivityEvent.objects.filter(event_type='label_removed').exists())

    def test_other_user_cannot_remove_label(self):
        label = CardLabel.objects.create(user=self.other_user, name='Private')
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('planner:label-remove', args=[self.block.pk, label.pk])
        )
        self.assertEqual(response.status_code, 404)
