import re

from django.contrib.auth import get_user_model

User = get_user_model()
MENTION_PATTERN = re.compile(r'@([\w.+-]+)')


def parse_mentioned_users(message):
    usernames = set(MENTION_PATTERN.findall(message))
    if not usernames:
        return User.objects.none()
    return User.objects.filter(username__in=usernames, is_active=True)


def create_design_comment(design, author, message):
    from .models import DesignComment

    comment = DesignComment.objects.create(design=design, author=author, message=message)
    mentioned = parse_mentioned_users(message)
    if mentioned.exists():
        comment.mentions.set(mentioned)
    return comment


def highlight_mentions(text):
    """Wrap @username in span for display."""
    return MENTION_PATTERN.sub(
        r'<span class="text-primary-light font-semibold">@\1</span>',
        text,
    )
