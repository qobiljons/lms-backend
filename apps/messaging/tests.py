from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import Course
from apps.groups.models import Group

from .models import DirectConversation, GroupConversation

class MessagingAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="admin@msg.com", username="admin_msg", password="pass12345", role="admin"
        )
        self.instructor = User.objects.create_user(
            email="inst@msg.com", username="inst_msg", password="pass12345", role="instructor"
        )
        self.student1 = User.objects.create_user(
            email="s1@msg.com", username="stud_msg_1", password="pass12345", role="student"
        )
        self.student2 = User.objects.create_user(
            email="s2@msg.com", username="stud_msg_2", password="pass12345", role="student"
        )

        self.course = Course.objects.create(title="Msg Course", description="d")
        self.group = Group.objects.create(name="Msg Group", instructor=self.instructor)
        self.group.students.add(self.student1)
        self.group.courses.add(self.course)

        self.client = APIClient()

    def test_any_user_can_direct_message_any_other_user(self):
        self.client.force_authenticate(user=self.student1)
        response = self.client.post(
            f"/messages/direct/{self.admin.id}/",
            {"body": "Hello admin"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conversation = DirectConversation.objects.get()
        self.assertEqual(conversation.messages.count(), 1)

    def test_reachable_users_list_for_non_admin(self):
        self.client.force_authenticate(user=self.student1)
        response = self.client.get("/messages/users/?search=admin")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [row["username"] for row in response.data["results"]]
        self.assertIn("admin_msg", usernames)

    def test_direct_conversation_reused(self):
        self.client.force_authenticate(user=self.student1)
        self.client.post(f"/messages/direct/{self.student2.id}/", {"body": "first"}, format="json")
        self.client.post(f"/messages/direct/{self.student2.id}/", {"body": "second"}, format="json")
        self.assertEqual(DirectConversation.objects.count(), 1)

    def test_group_chat_auto_created_for_new_group(self):
        group = Group.objects.create(name="Auto Group", instructor=self.instructor)
        self.assertTrue(GroupConversation.objects.filter(group=group).exists())

    def test_group_member_can_send_group_message(self):
        self.client.force_authenticate(user=self.student1)
        response = self.client.post(
            f"/messages/groups/{self.group.id}/",
            {"body": "hello team"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conversation = GroupConversation.objects.get(group=self.group)
        self.assertEqual(conversation.messages.count(), 1)

    def test_non_member_cannot_access_group_messages(self):
        self.client.force_authenticate(user=self.student2)
        response = self.client.get(f"/messages/groups/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
