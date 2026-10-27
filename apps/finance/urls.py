from django.urls import path

from apps.finance.views import (
    FeeStatusDetailView,
    FeeStatusListCreateView,
    FeeStructureDetailView,
    FeeStructureListCreateView,
    MyFeeStatusDetailView,
    MyFeeStatusListView,
    RecordFeePaymentView,
)

urlpatterns = [
    path("structures/", FeeStructureListCreateView.as_view(), name="structure-list"),
    path("structures/<int:pk>/", FeeStructureDetailView.as_view(), name="structure-detail"),
    path("me/fees/", MyFeeStatusListView.as_view(), name="my-fees"),
    path("me/fees/<int:pk>/", MyFeeStatusDetailView.as_view(), name="my-fee-detail"),
    path("statuses/", FeeStatusListCreateView.as_view(), name="status-list"),
    path("statuses/<int:pk>/", FeeStatusDetailView.as_view(), name="status-detail"),
    path(
        "statuses/<int:pk>/record-payment/",
        RecordFeePaymentView.as_view(),
        name="status-record-payment",
    ),
]
