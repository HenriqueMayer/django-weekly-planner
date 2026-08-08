"""Attachment validation and ownership tests."""

from datetime import time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.planner.models import ActivityEvent, CardAttachment, TimeBlock

User = get_user_model()


@override_settings(MEDIA_ROOT='/tmp/django-weekly-planner-test-media')
class AttachmentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.block = TimeBlock.objects.create(
            user=self.user, label='Project', day_of_week=0,
            start_time=time(9), end_time=time(10),
        )
        self.client.force_login(self.user)

    def test_upload_and_delete_attachment(self):
        upload = SimpleUploadedFile('notes.txt', b'launch notes')
        response = self.client.post(
            reverse('planner:attachment-add', args=[self.block.pk]),
            {'file': upload},
        )
        self.assertEqual(response.status_code, 200)
        attachment = CardAttachment.objects.get(time_block=self.block)
        self.assertEqual(attachment.original_name, 'notes.txt')
        self.assertTrue(ActivityEvent.objects.filter(event_type='attachment_added').exists())

        response = self.client.post(
            reverse('planner:attachment-delete', args=[self.block.pk, attachment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CardAttachment.objects.filter(pk=attachment.pk).exists())

    def test_invalid_extension_is_rejected(self):
        upload = SimpleUploadedFile('payload.exe', b'not allowed')
        response = self.client.post(
            reverse('planner:attachment-add', args=[self.block.pk]),
            {'file': upload},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CardAttachment.objects.exists())

    def test_other_user_cannot_delete_attachment(self):
        attachment = CardAttachment.objects.create(
            time_block=self.block,
            uploaded_by=self.user,
            file=SimpleUploadedFile('notes.txt', b'notes'),
            original_name='notes.txt',
        )
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('planner:attachment-delete', args=[self.block.pk, attachment.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CardAttachment.objects.filter(pk=attachment.pk).exists())
