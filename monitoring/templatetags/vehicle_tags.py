from django import template

register = template.Library()

@register.filter
def format_interval(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"Every {seconds} second{'s' if seconds != 1 else ''}"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"Every {minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"Every {hours} hour{'s' if hours != 1 else ''}"
    else:
        days = seconds // 86400
        return f"Every {days} day{'s' if days != 1 else ''}"