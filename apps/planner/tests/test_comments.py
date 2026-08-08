"""Card comment creation and ownership tests."""

from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import ActivityEvent, CardComment, TimeBlock

User = get_user_model()


class CommentViewTests(TestCase):
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

    def test_add_comment_persists_author_and_activity(self):
        response = self.client.post(
            reverse('planner:comment-add', args=[self.block.pk]),
            {'body': 'Remember to include the launch notes.'},
        )

        self.assertEqual(response.status_code, 200)
        comment = CardComment.objects.get(time_block=self.block)
        self.assertEqual(comment.author, self.user)
        self.assertTrue(
            ActivityEvent.objects.filter(
                time_block=self.block,
                event_type='comment_added',
            ).exists()
        )

    def test_other_user_cannot_add_comment(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('planner:comment-add', args=[self.block.pk]),
            {'body': 'Unauthorized'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(CardComment.objects.exists())

    def test_author_can_update_and_delete_comment(self):
        comment = CardComment.objects.create(
            time_block=self.block,
            author=self.user,
            body='Draft comment',
        )

        response = self.client.post(
            reverse('planner:comment-update', args=[self.block.pk, comment.pk]),
            {'body': 'Updated comment'},
        )
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.body, 'Updated comment')

        response = self.client.post(
            reverse('planner:comment-delete', args=[self.block.pk, comment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CardComment.objects.filter(pk=comment.pk).exists())

    def test_non_author_cannot_update_or_delete_comment(self):
        comment = CardComment.objects.create(
            time_block=self.block,
            author=self.other_user,
            body='Private author comment',
        )

        response = self.client.post(
            reverse('planner:comment-update', args=[self.block.pk, comment.pk]),
            {'body': 'Hijacked'},
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse('planner:comment-delete', args=[self.block.pk, comment.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CardComment.objects.filter(pk=comment.pk).exists())
