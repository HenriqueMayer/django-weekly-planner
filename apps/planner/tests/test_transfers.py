"""Card transfer validation and audit tests."""

from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import ActivityEvent, CardTransfer, TimeBlock

User = get_user_model()


class CardTransferTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='alice', password='pass12345')
        self.recipient = User.objects.create_user(username='bob', password='pass12345')
        self.block = TimeBlock.objects.create(
            user=self.owner, label='Shared project', day_of_week=0,
            start_time=time(9), end_time=time(10),
        )
        self.client.force_login(self.owner)

    def test_transfer_changes_owner_and_records_audit(self):
        response = self.client.post(
            reverse('planner:card-transfer', args=[self.block.pk]),
            {'recipient': self.recipient.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.block.refresh_from_db()
        self.assertEqual(self.block.user, self.recipient)
        self.assertTrue(CardTransfer.objects.filter(time_block=self.block).exists())
        self.assertTrue(ActivityEvent.objects.filter(event_type='card_transferred').exists())

    def test_transfer_rejects_destination_overlap(self):
        TimeBlock.objects.create(
            user=self.recipient, label='Conflict', day_of_week=0,
            start_time=time(9), end_time=time(10),
        )
        response = self.client.post(
            reverse('planner:card-transfer', args=[self.block.pk]),
            {'recipient': self.recipient.pk},
        )
        self.assertEqual(response.status_code, 400)
        self.block.refresh_from_db()
        self.assertEqual(self.block.user, self.owner)
