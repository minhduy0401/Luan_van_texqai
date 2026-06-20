# utils/policy_pages.py – Quản lý nội dung chính sách (file HTML, không qua database)
import os
import re

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMPLATES_DIR = os.path.join(_PROJECT_ROOT, 'templates')
_CONTENT_DIR = os.path.join(_TEMPLATES_DIR, 'policies', 'content')
_INSTANCE_DIR = os.path.join(_PROJECT_ROOT, 'instance')
_LEGAL_UPDATED_FILE = os.path.join(_INSTANCE_DIR, 'legal_updated.txt')

_MAX_POLICY_BYTES = 512 * 1024

_EMAIL_RE = re.compile(r'[\w.+-]+@[\w.-]+\.\w{2,}', re.IGNORECASE)

POLICY_PAGES = (
    {
        'slug': 'privacy',
        'filename': 'privacy.html',
        'endpoint': 'privacy',
        'title_vi': 'Chính sách quyền riêng tư',
        'title_en': 'Privacy Policy',
    },
    {
        'slug': 'terms',
        'filename': 'terms.html',
        'endpoint': 'terms',
        'title_vi': 'Điều khoản sử dụng',
        'title_en': 'Terms of Service',
    },
    {
        'slug': 'payment-policy',
        'filename': 'payment_policy.html',
        'endpoint': 'payment_policy',
        'title_vi': 'Chính sách thanh toán',
        'title_en': 'Payment Policy',
    },
    {
        'slug': 'ai-policy',
        'filename': 'ai_policy.html',
        'endpoint': 'ai_policy',
        'title_vi': 'Chính sách AI',
        'title_en': 'AI Policy',
    },
    {
        'slug': 'data-deletion',
        'filename': 'data_deletion.html',
        'endpoint': 'data_deletion',
        'title_vi': 'Xóa dữ liệu người dùng',
        'title_en': 'Data Deletion',
    },
)

_DEFAULT_LEGAL_UPDATED = '13/06/2026'

_IF_ELSE_RE = re.compile(
    r"\{%\s*if\s+current_lang\s*==\s*['\"]en['\"]\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}",
    re.DOTALL,
)
_INLINE_LANG_RE = re.compile(
    r"\{\{\s*'((?:\\'|[^'])*)'\s*if\s*current_lang\s*==\s*'en'\s*else\s*'((?:\\'|[^'])*)'\s*\}\}"
)
_CARD_BODY_RE = re.compile(
    r'(<div class="card-body p-0[^"]*"[^>]*>)(.*?)(</div>\s*\n\s*</div>\s*\n\s*<div class="text-center text-muted)',
    re.DOTALL,
)
def _normalize_policy_html(html: str) -> str:
    """Đồng bộ mailto cho email trong thẻ <a> và tự bọc email dạng text thuần."""
    if not html or '@' not in html:
        return html

    def _fix_anchor(match: re.Match) -> str:
        attrs = match.group(1)
        email = match.group(2)
        attrs = re.sub(r'\s*href="[^"]*"', '', attrs, flags=re.I)
        attrs = re.sub(r"\s*href='[^']*'", '', attrs, flags=re.I)
        attrs = attrs.strip()
        if attrs:
            return f'<a {attrs} href="mailto:{email}">{email}</a>'
        return f'<a href="mailto:{email}">{email}</a>'

    anchor_re = re.compile(
        rf'<a\b([^>]*)>\s*({_EMAIL_RE.pattern})\s*</a>',
        re.IGNORECASE,
    )
    html = anchor_re.sub(_fix_anchor, html)

    parts = re.split(r'(<[^>]+>)', html)
    in_anchor = 0
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith('<'):
            out.append(part)
            if re.match(r'<\s*a\b', part, re.I):
                in_anchor += 1
            elif re.match(r'<\s*/\s*a\s*>', part, re.I):
                in_anchor = max(0, in_anchor - 1)
        elif in_anchor:
            out.append(part)
        else:
            out.append(_EMAIL_RE.sub(
                lambda m: f'<a href="mailto:{m.group(0)}">{m.group(0)}</a>',
                part,
            ))
    return ''.join(out)


def _policy_by_slug(slug: str) -> dict | None:
    for item in POLICY_PAGES:
        if item['slug'] == slug:
            return item
    return None


def _resolve_template_path(filename: str) -> str:
    base = os.path.realpath(_TEMPLATES_DIR)
    path = os.path.realpath(os.path.join(_TEMPLATES_DIR, filename))
    if not path.startswith(base + os.sep) and path != base:
        raise ValueError('Invalid policy path')
    if os.path.basename(path) != filename:
        raise ValueError('Invalid policy filename')
    return path


def _content_path(slug: str, lang: str) -> str:
    if lang not in ('vi', 'en'):
        raise ValueError('Invalid language')
    if not _policy_by_slug(slug):
        raise KeyError(slug)
    os.makedirs(_CONTENT_DIR, exist_ok=True)
    return os.path.join(_CONTENT_DIR, f'{slug}_{lang}.html')


def _resolve_lang_html(fragment: str, lang: str) -> str:
    """Chuyển fragment Jinja song ngữ thành HTML một ngôn ngữ."""
    html = fragment
    for _ in range(200):
        m = _IF_ELSE_RE.search(html)
        if not m:
            break
        chosen = m.group(1) if lang == 'en' else m.group(2)
        html = html[: m.start()] + chosen.strip() + html[m.end() :]

    def _pick_inline(match: re.Match) -> str:
        return match.group(1) if lang == 'en' else match.group(2)

    html = _INLINE_LANG_RE.sub(_pick_inline, html)
    html = re.sub(r'\{%[^%]+%\}', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip() + '\n'


def _extract_card_inner(full_html: str) -> str:
    m = _CARD_BODY_RE.search(full_html)
    if not m:
        raise ValueError('Không tìm thấy vùng nội dung chính sách trong template')
    return m.group(2)


def _template_uses_includes(full_html: str, slug: str) -> bool:
    return f"policies/content/{slug}_vi.html" in full_html


def _template_uses_policy_body(full_html: str) -> bool:
    """Template shell đọc nội dung qua biến policy_body_vi/en (route render)."""
    return 'policy_body_vi' in full_html or 'policy_body_en' in full_html


def _template_content_is_external(full_html: str, slug: str) -> bool:
    """Nội dung đã tách ra file — không cần migrate từ template."""
    return _template_uses_includes(full_html, slug) or _template_uses_policy_body(full_html)


def _write_file_atomic(path: str, content: str) -> None:
    encoded = content.encode('utf-8')
    if len(encoded) > _MAX_POLICY_BYTES:
        raise ValueError(f'Nội dung vượt {_MAX_POLICY_BYTES // 1024} KB')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    os.replace(tmp, path)


def ensure_policy_split(slug: str) -> None:
    """Tách nội dung VI/EN ra file riêng (một lần) nếu template còn dạng cũ."""
    meta = _policy_by_slug(slug)
    if not meta:
        raise KeyError(slug)

    vi_path = _content_path(slug, 'vi')
    en_path = _content_path(slug, 'en')
    path = _resolve_template_path(meta['filename'])
    with open(path, encoding='utf-8') as f:
        full_html = f.read()

    if _template_content_is_external(full_html, slug):
        if not os.path.isfile(vi_path):
            _write_file_atomic(vi_path, '<p></p>\n')
        if not os.path.isfile(en_path):
            _write_file_atomic(en_path, '<p></p>\n')
        return

    if os.path.isfile(vi_path) and os.path.isfile(en_path):
        inner = _extract_card_inner(full_html)
        if 'current_lang' not in inner:
            return
    else:
        inner = _extract_card_inner(full_html)
        _write_file_atomic(vi_path, _resolve_lang_html(inner, 'vi'))
        _write_file_atomic(en_path, _resolve_lang_html(inner, 'en'))

    include_block = (
        "{% if current_lang == 'en' %}\n"
        f"        {{% include 'policies/content/{slug}_en.html' %}}\n"
        "        {% else %}\n"
        f"        {{% include 'policies/content/{slug}_vi.html' %}}\n"
        "        {% endif %}"
    )
    m = _CARD_BODY_RE.search(full_html)
    new_html = full_html[: m.start(2)] + '\n        ' + include_block + '\n      ' + full_html[m.end(2) :]
    _write_file_atomic(path, new_html)


def get_legal_updated(default: str = _DEFAULT_LEGAL_UPDATED) -> str:
    try:
        if os.path.isfile(_LEGAL_UPDATED_FILE):
            with open(_LEGAL_UPDATED_FILE, encoding='utf-8') as f:
                value = f.read().strip()
                if value:
                    return value
    except OSError:
        pass
    return default


def set_legal_updated(value: str) -> None:
    value = (value or '').strip()
    if not value:
        return
    os.makedirs(_INSTANCE_DIR, exist_ok=True)
    with open(_LEGAL_UPDATED_FILE, 'w', encoding='utf-8') as f:
        f.write(value)


def read_policy_content(slug: str, lang: str) -> str:
    ensure_policy_split(slug)
    path = _content_path(slug, lang)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding='utf-8') as f:
        return _normalize_policy_html(f.read())


def write_policy_content(slug: str, lang: str, content: str) -> None:
    ensure_policy_split(slug)
    if content is None:
        raise ValueError('Empty content')
    path = _content_path(slug, lang)
    body = _normalize_policy_html((content or '').strip())
    if body and not body.endswith('\n'):
        body += '\n'
    _write_file_atomic(path, body)


def write_policy_contents(slug: str, content_vi: str, content_en: str) -> None:
    write_policy_content(slug, 'vi', content_vi)
    write_policy_content(slug, 'en', content_en)


def list_policies_for_admin(lang: str = 'vi') -> list[dict]:
    items = []
    for p in POLICY_PAGES:
        items.append({
            **p,
            'title': p['title_en'] if lang == 'en' else p['title_vi'],
        })
    return items


def migrate_all_policies() -> None:
    for p in POLICY_PAGES:
        ensure_policy_split(p['slug'])
