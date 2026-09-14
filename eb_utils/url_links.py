from flask import g, current_app


def get_url_prefix() -> str:
    """从当前请求上下文获取 URL 前缀"""
    try:
        # 优先使用 lang_from_url 标志（与 index.py 的 inject_i18n_globals 保持一致）
        lang_from_url = getattr(g, 'lang_from_url', False)
        if lang_from_url:
            lang = getattr(g, 'lang', '')
            return f'/{lang}' if lang else ''
        return ''
    except Exception:
        return ''


def _localize(url: str) -> str:
    """根据当前语言给 URL 添加前缀"""
    prefix = get_url_prefix()
    if prefix and not url.startswith(prefix) and not url.startswith('http'):
        return prefix + url
    return url


def get_class_url(c_id: int, page_code: int = 1):
    return _localize(f'/c{c_id}p{page_code}.html')


def get_content_url(a_id: int):
    return _localize(f'/a{a_id}.html')


def get_special_url(c_id: int, page_code: int = 1):
    return _localize(f'/s{c_id}p{page_code}.html')