from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

FILTER_PARAMS = [
    OpenApiParameter(
        name="q",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Search by any keyword",
        required=False,
        default="*",
    ),
    OpenApiParameter(
        name="page",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Specify the page of the fetched list (`all` can be set to fetch all)",
        required=False,
        default=1,
    ),
    OpenApiParameter(
        name="limit",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Specify the limit for each page fetched",
        required=False,
        default=settings.DEFAULT_PAGE_SIZE,
    ),
    OpenApiParameter(
        name="order",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Sort fetched list",
        required=False,
        default="asc",
        enum=["asc", "desc"],
    ),
]

TOOLS_CATEGORY_PARAMS = FILTER_PARAMS + [
    OpenApiParameter(
        name="order_by",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Sort fetched list by",
        required=False,
        default="name",
        enum=["name", "description"],
    ),
    OpenApiParameter(
        name="my_tools",
        description="Filter by the current user's (technician) created tools",
        required=False,
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
    ),
]

TOOLS_PARAMS = FILTER_PARAMS + [
    OpenApiParameter(
        name="order_by",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Sort fetched list by",
        required=False,
        default="name",
        enum=["name", "description", "price"],
    ),
    OpenApiParameter(
        name="category",
        type=OpenApiTypes.UUID,
        location=OpenApiParameter.QUERY,
        description="Tool category to filter the fetched list by: UUID",
        required=False,
    ),
    OpenApiParameter(
        name="owner",
        type=OpenApiTypes.UUID,
        location=OpenApiParameter.QUERY,
        description="Filter fetched list by tool's owner (Technician) UUID",
        required=False,
    ),
    OpenApiParameter(
        name="my_tools",
        description="Filter by the current user's (technician) created tools",
        required=False,
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
    ),
    OpenApiParameter(
        name="others_tools",
        description="Filter to get only other technician's tools created",
        required=False,
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
    ),
]
