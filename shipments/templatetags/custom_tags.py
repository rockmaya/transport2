import calendar
from django import template


register = template.Library()

@register.filter
def in_group(user, group_name):
    return user.groups.filter(name=group_name).exists() or user.is_superuser


@register.filter
def month_name(value):
    """
    Convert a month number (1-12) to its name.
    """
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    try:
        return months[int(value) - 1]
    except (IndexError, ValueError, TypeError):
        return ""
    

@register.filter
def days_in_month(month_year):
    """
    month_year: dict or object with fields month, year
    """
    try:
        year = int(month_year.year)
        month = int(month_year.month)
        return calendar.monthrange(year, month)[1]
    except Exception:
        return 30  # fallback
    
@register.filter
def mul(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
