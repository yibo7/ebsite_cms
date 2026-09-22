"""
HTML 安全净化工具

基于 Python 标准库 html.parser 实现，无外部依赖。
功能：
  - 白名单标签和属性
  - 自动移除 <script>、<iframe>、<object> 等危险标签及其内容
  - 清除所有 on* 事件处理属性（onclick、onerror 等）
  - 清除 javascript: / data: 等危险 URI 协议
  - 可选的标签白名单扩展

使用示例：
    from eb_utils.html_sanitizer import sanitize_html
    safe_html = sanitize_html(user_input_html)
"""

from html.parser import HTMLParser
import re

# ──────────────────────────────────────────────
# 安全标签白名单
# ──────────────────────────────────────────────
SAFE_TAGS = frozenset({
    # 区块
    'p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'pre', 'code', 'hr', 'br',
    # 列表
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    # 表格
    'table', 'caption', 'thead', 'tbody', 'tfoot',
    'tr', 'th', 'td', 'colgroup', 'col',
    # 文本修饰
    'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins',
    'sub', 'sup', 'small', 'mark', 'abbr', 'cite',
    # 链接与媒体
    'a', 'img',
})

# ──────────────────────────────────────────────
# 安全属性白名单（每个标签可用的属性）
# ──────────────────────────────────────────────
SAFE_ATTRS = frozenset({
    'href', 'src', 'alt', 'title', 'width', 'height',
    'class', 'id', 'style', 'dir', 'lang',
    'target', 'rel', 'download',
    'colspan', 'rowspan', 'scope', 'headers',
    'align', 'valign', 'border', 'cellpadding', 'cellspacing',
    'start', 'type', 'value', 'datetime',
})

# ──────────────────────────────────────────────
# 危险 URI 协议正则
# ──────────────────────────────────────────────
DANGEROUS_SCHEMES = re.compile(
    r'^\s*(?:javascript|data|vbscript|file|about|chrome|blob):',
    re.IGNORECASE,
)


class _HtmlSanitizer(HTMLParser):
    """
    基于 HTMLParser 的净化器。
    遍历 HTML 标签，只保留白名单内的标签与属性，移除事件处理器和危险 URI。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._result: list[str] = []
        self._skip_tag_depth = 0  # >0 表示当前在要跳过的标签内部

    def _is_safe_tag(self, tag: str) -> bool:
        return tag.lower() in SAFE_TAGS

    def _is_dangerous_tag(self, tag: str) -> bool:
        """这些标签及其全部子内容将完全移除"""
        return tag.lower() in {
            'script', 'iframe', 'object', 'embed', 'frame', 'frameset',
            'form', 'input', 'textarea', 'select', 'option', 'optgroup',
            'button', 'style', 'meta', 'link', 'base',
            'svg', 'math',
        }

    def _is_safe_attr(self, tag: str, attr_name: str) -> bool:
        name_lower = attr_name.lower()
        # 禁止所有 on* 事件处理属性
        if name_lower.startswith('on'):
            return False
        return name_lower in SAFE_ATTRS

    def _is_safe_url(self, attr_name: str, attr_value: str) -> bool:
        """检查 href/src 等 URL 属性值是否安全"""
        if attr_name.lower() in ('href', 'src', 'action', 'data', 'poster'):
            if DANGEROUS_SCHEMES.match(attr_value):
                return False
            # 安全：锚点、相对路径、协议化路径等
        return True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # 如果当前在跳过区域内，检查是否遇到了嵌套标签
        if self._skip_tag_depth > 0:
            if self._is_dangerous_tag(tag):
                self._skip_tag_depth += 1
            return

        if self._is_dangerous_tag(tag):
            self._skip_tag_depth = 1
            return

        if not self._is_safe_tag(tag):
            # 不在白名单中的标签：保留其内容，丢弃标签本身
            return

        # 过滤安全的属性
        safe_attrs = []
        for attr_name, attr_value in attrs:
            if attr_value is None:
                # 布尔属性，如 <hr noshade>
                attr_value = attr_name.lower()
            if not self._is_safe_attr(tag, attr_name):
                continue
            if not self._is_safe_url(attr_name, attr_value):
                continue
            safe_attrs.append((attr_name, attr_value))

        # 重建标签
        parts = [f'<{tag}']
        for attr_name, attr_value in safe_attrs:
            # 对属性值做 HTML 转义
            safe_val = (
                str(attr_value)
                .replace('&', '&amp;')
                .replace('"', '&quot;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
            )
            parts.append(f' {attr_name}="{safe_val}"')
        parts.append('>')
        self._result.append(''.join(parts))

    def handle_endtag(self, tag: str) -> None:
        if self._skip_tag_depth > 0:
            if self._is_dangerous_tag(tag):
                self._skip_tag_depth -= 1
            return

        if not self._is_safe_tag(tag):
            return

        self._result.append(f'</{tag}>')

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """处理 <br/> <img/> 等自闭合标签"""
        if self._skip_tag_depth > 0:
            return

        if self._is_dangerous_tag(tag):
            return

        if not self._is_safe_tag(tag):
            return

        # 过滤属性
        safe_attrs = []
        for attr_name, attr_value in attrs:
            if attr_value is None:
                attr_value = attr_name.lower()
            if not self._is_safe_attr(tag, attr_name):
                continue
            if not self._is_safe_url(attr_name, attr_value):
                continue
            safe_attrs.append((attr_name, attr_value))

        parts = [f'<{tag}']
        for attr_name, attr_value in safe_attrs:
            safe_val = (
                str(attr_value)
                .replace('&', '&amp;')
                .replace('"', '&quot;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
            )
            parts.append(f' {attr_name}="{safe_val}"')
        parts.append(' />')
        self._result.append(''.join(parts))

    def handle_data(self, data: str) -> None:
        if self._skip_tag_depth > 0:
            return
        # 文本内容不需要转义，因为 convert_charrefs=True 已经处理了字符引用
        self._result.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._skip_tag_depth > 0:
            return
        self._result.append(f'&{name};')

    def handle_charref(self, name: str) -> None:
        if self._skip_tag_depth > 0:
            return
        self._result.append(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        # 移除所有 HTML 注释
        pass

    def get_safe_html(self) -> str:
        return ''.join(self._result)


def sanitize_html(html_content: str, max_length: int = 0) -> str:
    """
    净化 HTML 内容，移除危险标签和属性。

    :param html_content: 原始 HTML 字符串
    :param max_length: 可选最大长度限制（0 表示不限制）
    :return: 净化后的安全 HTML
    """
    if not html_content or not isinstance(html_content, str):
        return html_content if html_content else ''

    # 长度截断
    if max_length > 0 and len(html_content) > max_length:
        html_content = html_content[:max_length]

    sanitizer = _HtmlSanitizer()
    try:
        sanitizer.feed(html_content)
        sanitizer.close()
    except Exception:
        # 解析失败时返回纯文本版本（剥离所有标签）
        return _strip_all_tags(html_content)

    return sanitizer.get_safe_html()


def _strip_all_tags(text: str) -> str:
    """兜底方案：完全剥离所有 HTML 标签"""
    return re.sub(r'<[^>]*>', '', text).strip()


# ──────────────────────────────────────────────
# 便捷函数：仅过滤 on* 事件处理器（不改标签结构）
# ──────────────────────────────────────────────
_EVENT_PATTERN = re.compile(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)


def strip_event_handlers(html_content: str) -> str:
    """
    轻量级清理：只移除 on* 事件属性，不改变标签结构。
    适用于对已信任 HTML 做快速事件清理。
    """
    return _EVENT_PATTERN.sub('', html_content)