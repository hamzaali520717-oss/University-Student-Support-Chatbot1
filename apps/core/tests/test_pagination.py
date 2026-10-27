from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.pagination import DefaultPagination

factory = APIRequestFactory()


def _paginate(queryset, query_string=""):
    django_request = factory.get(f"/{query_string}")
    request = Request(django_request)
    paginator = DefaultPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator, page


class DefaultPaginationTests(SimpleTestCase):
    def test_default_page_size(self):
        _, page = _paginate(list(range(50)))
        self.assertEqual(len(page), 20)

    def test_page_size_query_param(self):
        _, page = _paginate(list(range(50)), "?page_size=5")
        self.assertEqual(len(page), 5)

    def test_max_page_size_cap(self):
        _, page = _paginate(list(range(500)), "?page_size=1000")
        self.assertEqual(len(page), 100)

    def test_paginated_response_shape(self):
        paginator, page = _paginate(list(range(5)))
        response = paginator.get_paginated_response(page)
        self.assertEqual(
            set(response.data.keys()), {"count", "next", "previous", "results"}
        )
        self.assertEqual(response.data["count"], 5)
