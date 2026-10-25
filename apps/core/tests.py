from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")

    def test_home_page_loads_application_stylesheet(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "css/app.css")
        self.assertContains(response, "vendor/bootstrap/bootstrap.min.css")
