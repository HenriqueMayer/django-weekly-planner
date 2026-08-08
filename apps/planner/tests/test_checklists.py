"""Checklist item CRUD and ownership tests."""

from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import ActivityEvent, ChecklistItem, TimeBlock

User = get_user_model()


class ChecklistViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.block = TimeBlock.objects.create(
            user=self.user,
            label='Project',
            day_of_week=0,
            start_time=time(9),
            end_time=time(10),
        )
        self.client.force_login(self.user)

    def test_add_item_persists_and_records_activity(self):
        response = self.client.post(
            reverse('planner:checklist-add', args=[self.block.pk]),
            {'text': 'Review notes'},
        )

        self.assertEqual(response.status_code, 200)
        item = ChecklistItem.objects.get(time_block=self.block)
        self.assertEqual(item.position, 0)
        self.assertTrue(
            ActivityEvent.objects.filter(
                time_block=self.block,
                event_type='checklist_item_added',
            ).exists()
        )

    def test_toggle_and_delete_item(self):
        item = ChecklistItem.objects.create(time_block=self.block, text='Send report')

        response = self.client.post(
            reverse('planner:checklist-toggle', args=[self.block.pk, item.pk])
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_completed)

        response = self.client.post(
            reverse('planner:checklist-delete', args=[self.block.pk, item.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChecklistItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(
            ActivityEvent.objects.filter(
                time_block=self.block,
                event_type='checklist_item_deleted',
            ).exists()
        )

    def test_other_user_cannot_mutate_item(self):
        item = ChecklistItem.objects.create(time_block=self.block, text='Private')
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse('planner:checklist-toggle', args=[self.block.pk, item.pk])
        )

        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertFalse(item.is_completed)
