""" Custom django template tags. """


from django import template
from django.template.defaultfilters import linebreaks, stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

import bleach
from bleach import callbacks

register = template.Library()  # pylint: disable=invalid-name


@register.filter()
@stringfilter
def link_and_linebreak(text):
    """
    Converts URLs in text into clickable links with their target attribute set to `_blank`.
    It wraps givent tags into <p> tags and converts line breaks(\n) to <br> tags.
    Args:
        text: (str) Text having URLs to be converted
    Returns: (str) Text with URLs convert to links
    """
    if text:
        escaped_text = conditional_escape(text)
        return mark_safe(linebreaks(bleach.linkify(escaped_text, callbacks=[callbacks.target_blank])))
    return None

@register.filter()
@stringfilter
def beautiful_minutes(minutes):
    int_minutes = 0
    try:
        int_minutes = int(minutes)
    except:
        return "Invalid estimated time."
    
    WEEK_MINUTES = 10080
    DAY_MINUTES = 1440
    HOUR_MINUTES = 60
    
    weeks = int_minutes // WEEK_MINUTES
    days = int_minutes // DAY_MINUTES if weeks == 0 else (int_minutes - WEEK_MINUTES * weeks) // DAY_MINUTES
    hours = 0 if weeks > 0 else int_minutes // HOUR_MINUTES if days == 0 else (int_minutes - days * DAY_MINUTES) // HOUR_MINUTES
    minutes = 0 if (weeks > 0 or days > 0) else int_minutes if hours == 0 else int_minutes % HOUR_MINUTES

    def generate_time_string(number, unit):
        if number == 0: 
            return ""
        elif number == 1:
            return f"1 {gettext_lazy(unit)}"
        else:
            return f"{number} {gettext_lazy(unit + 's')}"
        
    output = ""

    if weeks > 0:
        output += generate_time_string(weeks, "week")
        output += " "
        output += generate_time_string(days, "day")

    elif days > 0:
        output += generate_time_string(days, "day")
        output += " "
        output += generate_time_string(hours, "hour")

    elif hours > 0:
        output += generate_time_string(hours, "hour")
        output += " "
        output += generate_time_string(minutes, "minute")

    else:
        output += generate_time_string(minutes, "minute")

    return output
