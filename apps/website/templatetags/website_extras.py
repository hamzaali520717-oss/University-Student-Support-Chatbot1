from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def pkr(value: Decimal | None) -> str:
    """Format a decimal amount as localized PKR currency, e.g. 50000.00 -> 'PKR 50,000'."""
    if value is None:
        return ""
    return f"PKR {value:,.0f}"
