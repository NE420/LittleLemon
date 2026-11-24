"""
Template helpers that connect menu items to the photos in the media folder.

MenuItem has no image field, so a photo is matched by name: the drink
"Iced coffee" uses media/Iced_coffee.jpg. Case, spaces, underscores and
hyphens are ignored, and .jpg/.jpeg/.png/.webp/.avif all work.
"""
import os
import re
from urllib.parse import quote

from django import template
from django.conf import settings

register = template.Library()

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".avif")


def _key(text):
    """'Iced coffee', 'iced_coffee' and 'Iced-Coffee' all become 'icedcoffee'."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _media_files():
    root = getattr(settings, "MEDIA_ROOT", None)
    if not root or not os.path.isdir(root):
        return []
    return sorted(name for name in os.listdir(root) if name.lower().endswith(IMAGE_EXTENSIONS))


def _url(name):
    return f"{settings.MEDIA_URL}{quote(name)}"


@register.filter
def drink_image(title):
    """The URL of the photo for a drink, or '' when there isn't one."""
    key = _key(title)
    if not key:
        return ""
    wanted = {key, key.rstrip("s")}  # "Teas" still finds Tea.jpg
    for name in _media_files():
        stem = _key(os.path.splitext(name)[0])
        if stem in wanted or stem.rstrip("s") in wanted:
            return _url(name)
    return ""


@register.simple_tag
def media_gallery(limit=3):
    """The first few photos in the media folder, for the dashboard."""
    photos = []
    for name in _media_files()[: int(limit)]:
        label = os.path.splitext(name)[0].replace("_", " ").replace("-", " ").strip()
        photos.append({"url": _url(name), "label": label[:1].upper() + label[1:].lower()})
    return photos
