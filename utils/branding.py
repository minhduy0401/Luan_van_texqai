# utils/branding.py – Site shell: logo, favicon, name, description
import os
import time

BRANDING_SUBDIR = 'branding'
DEFAULTS_SUBDIR = 'branding/defaults'
DEFAULT_LOGO = 'logo.png'
DEFAULT_FAVICON = 'favicon.ico'
DEFAULT_FAVICON_32 = 'favicon-32.png'
DEFAULT_APPLE_TOUCH = 'apple-touch-icon.png'

ALLOWED_LOGO_EXTS = frozenset({'png', 'jpg', 'jpeg', 'webp', 'svg'})
ALLOWED_FAVICON_EXTS = frozenset({'ico', 'png', 'jpg', 'jpeg', 'webp', 'svg'})

PUBLIC_FAVICON_TARGETS = (
    'favicon.ico',
    'favicon-32.png',
    'apple-touch-icon.png',
)

DEFAULT_PUBLIC_FILES = {
    'favicon': PUBLIC_FAVICON_TARGETS,
    'logo': (DEFAULT_LOGO,),
}

DEFAULTS = {
    'site_name': 'TEXTQAI',
    'site_title_vi': 'Hệ thống sinh câu hỏi tự động',
    'site_title_en': 'Automatic Question Generation System',
    'site_description_vi': (
        'Hệ thống sinh câu hỏi tự động theo thang Bloom — hỗ trợ giảng viên tạo đề thi nhanh, '
        'chính xác và đúng chuẩn giáo dục từ tài liệu PDF.'
    ),
    'site_description_en': (
        "Automatic question generation based on Bloom's taxonomy — helping educators build tests "
        'rapidly, accurately, and aligned with standard pedagogy from PDF documents.'
    ),
    'site_logo': '',
    'site_favicon': '',
    'site_branding_version': '1',
}


def _stored_or_default(stored: str, default: str) -> str:
    s = (stored or '').strip()
    return s if s else default


def get_branding_version() -> str:
    from utils.app_settings import get_setting
    return get_setting('site_branding_version', DEFAULTS['site_branding_version'])


def bump_branding_version() -> None:
    from models import SystemSetting
    SystemSetting.set('site_branding_version', str(int(time.time())))


def mime_for_path(rel_path: str) -> str:
    ext = rel_path.rsplit('.', 1)[-1].lower() if '.' in rel_path else 'ico'
    return {
        'ico': 'image/vnd.microsoft.icon',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
    }.get(ext, 'image/png')


def _copy_file(src: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(src, 'rb') as sf, open(dest, 'wb') as df:
        df.write(sf.read())


def _defaults_path(static_folder: str, name: str) -> str:
    return os.path.join(static_folder, DEFAULTS_SUBDIR.replace('/', os.sep), name)


def ensure_default_asset_backups(static_folder: str, kind: str) -> None:
    """Keep pristine defaults before first custom overwrite."""
    names = DEFAULT_PUBLIC_FILES.get(kind, ())
    for name in names:
        backup = _defaults_path(static_folder, name)
        if os.path.isfile(backup):
            continue
        public = os.path.join(static_folder, name)
        if os.path.isfile(public):
            _copy_file(public, backup)


def restore_default_public_files(static_folder: str, kind: str) -> None:
    """Restore default logo/favicon files to static root from branding/defaults/."""
    names = DEFAULT_PUBLIC_FILES.get(kind, ())
    for name in names:
        backup = _defaults_path(static_folder, name)
        public = os.path.join(static_folder, name)
        if os.path.isfile(backup):
            _copy_file(backup, public)


def sync_favicon_public_copies(static_folder: str, rel_path: str) -> None:
    """Copy custom favicon to well-known static paths browsers request directly."""
    ensure_default_asset_backups(static_folder, 'favicon')
    src = os.path.join(static_folder, rel_path.replace('/', os.sep))
    if not os.path.isfile(src):
        return
    for name in PUBLIC_FAVICON_TARGETS:
        _copy_file(src, os.path.join(static_folder, name))


def clear_custom_favicon_files(static_folder: str) -> None:
    branding_dir = os.path.join(static_folder, BRANDING_SUBDIR)
    if not os.path.isdir(branding_dir):
        return
    for name in os.listdir(branding_dir):
        if name.startswith('favicon.'):
            try:
                os.remove(os.path.join(branding_dir, name))
            except OSError:
                pass


def restore_default_favicon(static_folder: str) -> None:
    clear_custom_favicon_files(static_folder)
    restore_default_public_files(static_folder, 'favicon')


def clear_custom_logo_files(static_folder: str) -> None:
    branding_dir = os.path.join(static_folder, BRANDING_SUBDIR)
    if not os.path.isdir(branding_dir):
        return
    for name in os.listdir(branding_dir):
        if name.startswith('logo.'):
            try:
                os.remove(os.path.join(branding_dir, name))
            except OSError:
                pass


def restore_default_logo(static_folder: str) -> None:
    clear_custom_logo_files(static_folder)
    restore_default_public_files(static_folder, 'logo')


def resolve_branding(lang: str = 'vi') -> dict:
    from utils.app_settings import get_setting

    name = get_setting('site_name', DEFAULTS['site_name']).strip() or DEFAULTS['site_name']
    title_vi = get_setting('site_title_vi', DEFAULTS['site_title_vi'])
    title_en = get_setting('site_title_en', DEFAULTS['site_title_en'])
    meta_vi = get_setting('site_description_vi', DEFAULTS['site_description_vi'])
    meta_en = get_setting('site_description_en', DEFAULTS['site_description_en'])
    title = title_en if lang == 'en' else title_vi
    meta = meta_en if lang == 'en' else meta_vi
    page_title = f'{name} – {title}' if title else name

    logo_file = _stored_or_default(get_setting('site_logo', ''), DEFAULT_LOGO)
    favicon_file = _stored_or_default(get_setting('site_favicon', ''), DEFAULT_FAVICON)
    custom_favicon = bool(get_setting('site_favicon', '').strip())

    favicon_32 = favicon_file if custom_favicon else DEFAULT_FAVICON_32
    apple_touch = favicon_file if custom_favicon else DEFAULT_APPLE_TOUCH
    favicon_type = mime_for_path(favicon_file)

    return {
        'site_name': name,
        'site_title': title,
        'site_title_vi': title_vi,
        'site_title_en': title_en,
        'site_page_title': page_title,
        'site_meta_description': meta,
        'site_description': meta,
        'site_description_vi': meta_vi,
        'site_description_en': meta_en,
        'site_logo_file': logo_file,
        'site_favicon_file': favicon_file,
        'site_favicon_32_file': favicon_32,
        'site_apple_touch_file': apple_touch,
        'site_favicon_type': favicon_type,
        'branding_v': get_branding_version(),
    }


def save_branding_upload(file_storage, kind: str, static_folder: str) -> str:
    """Save uploaded logo/favicon under static/branding/. Returns path relative to static/."""
    if not file_storage or not (file_storage.filename or '').strip():
        return ''
    original = file_storage.filename.strip()
    if '.' not in original:
        raise ValueError('invalid_extension')
    ext = original.rsplit('.', 1)[-1].lower()
    allowed = ALLOWED_LOGO_EXTS if kind == 'logo' else ALLOWED_FAVICON_EXTS
    if ext not in allowed:
        raise ValueError('invalid_extension')

    dest_dir = os.path.join(static_folder, BRANDING_SUBDIR)
    os.makedirs(dest_dir, exist_ok=True)
    rel = f'{BRANDING_SUBDIR}/{kind}.{ext}'
    dest_path = os.path.join(static_folder, rel.replace('/', os.sep))
    file_storage.save(dest_path)
    if not os.path.isfile(dest_path) or os.path.getsize(dest_path) == 0:
        raise ValueError('save_failed')
    return rel.replace('\\', '/')


def favicon_static_parts(static_root: str) -> tuple[str, str]:
    """Return (directory, filename) for send_from_directory."""
    from utils.app_settings import get_setting
    rel = _stored_or_default(get_setting('site_favicon', ''), DEFAULT_FAVICON)
    full = os.path.join(static_root, rel)
    directory = os.path.dirname(full)
    filename = os.path.basename(full)
    return directory, filename
