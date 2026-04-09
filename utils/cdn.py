import base64
import hashlib
import logging
import os
import time
from urllib.parse import quote

from django.conf import settings

logger = logging.getLogger("sounds")


def generate_cdn_download_url(sound):
    """Generate a time-limited signed URL for CDN download.

    Uses the nginx secure_link format: MD5(expires + uri + secret), base64url-encoded.
    Returns None if the original sound file does not exist on disk (caller should
    fall back to sendfile, which handles preview substitution).
    """
    sound_path = sound.locations("path")
    if not os.path.exists(sound_path):
        return None

    expires = int(time.time()) + settings.CDN_DOWNLOAD_URL_LIFETIME
    folder_id = str(sound.id // 1000)
    uri = f"/sounds/{folder_id}/{sound.id}.{sound.type}"

    # Must match nginx secure_link_md5 expression: "$secure_link_expires$uri$cdn_secret"
    string_to_sign = f"{expires}{uri}{settings.CDN_SECURE_LINK_SECRET}"
    md5_digest = hashlib.md5(string_to_sign.encode()).digest()
    md5_base64 = base64.urlsafe_b64encode(md5_digest).rstrip(b"=").decode()

    friendly_name = quote(sound.friendly_filename())
    return f"{settings.CDN_DOWNLOADS_BASE_URL}{uri}?md5={md5_base64}&expires={expires}&filename={friendly_name}"


def create_cdn_symlink(sound):
    """Create a CDN symlink for a sound: {id_folder}/{sound_id}.{type} -> actual file.

    The symlink hides the user_id from the CDN URL. Uses relative paths so the
    symlink works across different mount points (web vs CDN container).
    """
    sound_path = sound.locations("path")
    if not os.path.exists(sound_path):
        return False

    folder_id = str(sound.id // 1000)
    symlink_dir = os.path.join(settings.CDN_SOUNDS_SYMLINKS_PATH, folder_id)
    symlink_path = os.path.join(symlink_dir, f"{sound.id}.{sound.type}")

    os.makedirs(symlink_dir, exist_ok=True)
    # Relative target: ../../sounds/{folder}/{sound_id}_{user_id}.{type}
    target = os.path.relpath(sound_path, symlink_dir)
    try:
        os.symlink(target, symlink_path)
        return True
    except FileExistsError:
        return False


def delete_cdn_symlink(sound):
    """Remove the CDN symlink for a sound, if it exists."""
    folder_id = str(sound.id // 1000)
    symlink_path = os.path.join(settings.CDN_SOUNDS_SYMLINKS_PATH, folder_id, f"{sound.id}.{sound.type}")
    try:
        os.unlink(symlink_path)
    except FileNotFoundError:
        pass
