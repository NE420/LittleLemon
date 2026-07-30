from django.test import TestCase
from django.urls import reverse


class FrontendViewsTests(TestCase):
    def test_index_page_renders_dashboard_link_to_home(self):
        response = self.client.get(reverse('frontend:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/"')
        self.assertContains(response, '<a class="nav-link" href="/">Dashboard</a>')

    def test_cart_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse('frontend:cart'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your cart is empty right now.')
