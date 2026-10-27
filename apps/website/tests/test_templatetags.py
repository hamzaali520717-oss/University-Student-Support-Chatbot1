from decimal import Decimal

from django.test import SimpleTestCase

from apps.website.templatetags.website_extras import pkr


class PkrFilterTests(SimpleTestCase):
    def test_formats_with_thousands_separator_and_no_decimals(self):
        self.assertEqual(pkr(Decimal("50000.00")), "PKR 50,000")

    def test_formats_small_amount(self):
        self.assertEqual(pkr(Decimal("500")), "PKR 500")

    def test_none_returns_empty_string(self):
        self.assertEqual(pkr(None), "")
