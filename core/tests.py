from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    """Tests for the homepage view."""

    def test_homepage_status_code(self):
        """Test that the homepage returns a 200 status code."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_homepage_template(self):
        """Test that the homepage uses the correct template."""
        response = self.client.get(reverse("core:home"))
        self.assertTemplateUsed(response, "index.html")
        self.assertTemplateUsed(response, "base.html")

    def test_homepage_contains_correct_html(self):
        """Test that the homepage contains the expected HTML."""
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "SentinelIQ")
        self.assertContains(response, "Bem-vindo")
