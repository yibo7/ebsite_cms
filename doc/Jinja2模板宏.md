# Jinja2 模板宏 — 使用教程

`website/pages_admin/themes/default/templates/jinja2_ctrs/` 目录存放的是**可复用的 Jinja2 宏文件**，封装了后台管理界面中常见的 UI 组件（富文本编辑器、图片上传、文件上传等）。

宏（Macro）是 Jinja2 的"函数"——你在模板中调用它，它生成一段 HTML。相比直接手写 HTML+JS，宏提供了：

- **一致性**：所有页面使用同一套代码，样式统一
- **开箱即用**：引入一行宏，编辑器/上传组件就带图片上传、粘贴拦截等功能
- **易维护**：修复一个 bug 或升级版本，改一个文件所有页面生效

---

## 一、使用方法

在任何需要的地方（包括部件的 `admin.html`），用 `{% from %}` 导入你需要的宏即可：

```jinja
{% from "jinja2_ctrs/_upload_macros.html" import upload_assets, img_upload_multi %}
```

**注意事项：**

- 宏内的 `{{ admin_path }}` 由后台 Blueprint 的上下文处理器注入，**无需额外传参**
- 宏的 HTML/JS 资源通过 CDN 引入，**无需手动加载任何 CSS 或 JS 文件**
- 如果宏需要在页面中只加载一次资源（如富文本编辑器的 JS），宏内部会自动用 `g.setdefault()` 去重

---

## 二、上传组件 — `_upload_macros.html`

封装了基于 WebUploader 的图片/文件上传组件。包含 5 个上传宏和 1 个资源加载宏。

### 2.1 upload_assets()

加载上传组件所需的 CSS 和 JS。**每个页面只需调用一次**，放在 `<head>` 区域或正文最前面。

```jinja
{% from "jinja2_ctrs/_upload_macros.html" import upload_assets %}
{{ upload_assets() }}
```

### 2.2 img_upload(name, value, show_name, width, height)

**单图上传控件** — 选择一张图片，隐藏字段存储图片 URL，带缩略图预览。

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | — | 表单字段名，也是隐藏 input 的 id |
| `value` | 否 | `''` | 当前图片 URL，用于编辑回显 |
| `show_name` | 否 | `'上传图片'` | 标签文字 |
| `width` | 否 | `80` | 缩略图宽度 |
| `height` | 否 | `80` | 缩略图高度 |

**示例：**

```jinja
{{ img_upload('cover', model.cover, '封面图片', 120, 120) }}
```

### 2.3 img_upload_multi(name, value, show_name, width, height)

**多图上传控件** — 可批量选择多张图片，支持拖拽排序（由 WebUploader 提供）。

| 参数 | 说明同 `img_upload` |
|------|---------------------|

**示例：**（图集部件 `sys_7_picbox` 的使用方式）

```jinja
{% from "jinja2_ctrs/_upload_macros.html" import upload_assets, img_upload_multi %}
{{ upload_assets() }}

{{ img_upload_multi('info', model.info, '上传图片', 80, 80) }}
```

### 2.4 img_upload_path(name, value, show_name)

**单图上传-显示路径** — 选择图片后在文本框中显示文件路径，适合需要看到具体 URL 的场景。

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | — | 表单字段名 |
| `value` | 否 | `''` | 当前路径，编辑回显 |
| `show_name` | 否 | `'上传图片（显示路径）'` | 标签文字 |

**示例：**

```jinja
{{ img_upload_path('logo', model.logo, '网站 Logo') }}
```

### 2.5 file_upload(name, value, show_name)

**单文件上传控件** — 上传一个文件（任意类型），隐藏字段存储文件 URL。

| 参数 | 说明 |
|------|------|
| `name` | 表单字段名 |
| `value` | 当前文件 URL，编辑回显 |
| `show_name` | 标签文字，默认 `'上传文件'` |

### 2.6 file_upload_multi(name, value, show_name)

**多文件上传控件** — 可批量上传多个文件。

---

## 三、富文本编辑器组件

系统内置了三款富文本编辑器，可按需选用。

### 3.1 wangEditor — `_wangeditor_macro.html`

轻量级富文本编辑器（wangEditor-next v6），推荐用于**内容编辑、文章正文**等场景。

**资源宏：`wangeditor_assets()`**

```jinja
{% from "jinja2_ctrs/_wangeditor_macro.html" import wangeditor_assets, wangeditor_editor %}

{# 1. 加载资源（全页一次） #}
{{ wangeditor_assets() }}

{# 2. 渲染编辑器 #}
{{ wangeditor_editor('content', model.content, '500px', '请输入文章内容...') }}
```

`wangeditor_editor(name, content, height, placeholder)` 参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | — | 表单字段名，提交时从此字段取值 |
| `content` | 否 | `''` | 初始 HTML 内容，编辑回显用 |
| `height` | 否 | `'500px'` | 编辑器高度（CSS 单位） |
| `placeholder` | 否 | `'请输入内容...'` | 占位提示文字 |

**特性：**
- 工具栏：标题、加粗、斜体、引用、代码块、列表、图片上传、链接、表格等
- 图片上传自动 POST 到 `/api/upfile?t=img`，支持粘贴上传
- 表单提交时自动同步内容到隐藏字段
- 图片上传限制 5MB

### 3.2 Quill — `_quill_macro.html`

功能强大的富文本编辑器（Quill v2），支持**三档工具栏配置**。

**资源宏：`quill_assets()`**

```jinja
{% from "jinja2_ctrs/_quill_macro.html" import quill_assets, quill_editor %}

{{ quill_assets() }}

{{ quill_editor('body', model.body, '400px', '请输入...', mode='standard') }}
```

`quill_editor(name, content, height, placeholder, mode, enableImageUpload)` 参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | — | 表单字段名 |
| `content` | 否 | `''` | 初始 HTML 内容 |
| `height` | 否 | `'300px'` | 编辑器高度 |
| `placeholder` | 否 | `'请输入内容...'` | 占位文字 |
| `mode` | 否 | `'standard'` | 工具栏模式：`simple` / `standard` / `powerful` |
| `enableImageUpload` | 否 | `true` | 是否启用图片上传 |

**三档工具栏说明：**

| 模式 | 适用场景 | 功能 |
|------|---------|------|
| `simple` | 评论、短描述、备注 | 粗体、斜体、下划线、列表、链接、清除 |
| `standard`（默认） | 文章、CMS 正文 | simple + 删除线、引用、代码块、图片、标题、颜色 |
| `powerful` | 长文档、精细排版 | standard + 视频、公式、待办、上标/下标、缩进、字号 |

**特性：**
- 图片上传自动 POST 到 `/api/upfile?t=img`
- 粘贴图片自动拦截并上传（不会存为 base64）
- 表单提交时自动同步内容

---

## 四、在自定义页面中使用

不仅限于部件 `admin.html`，在任何后台页面的模板中都可以使用：

```jinja
{% extends 'base_admin.html' %}

{% block content %}
{% from "jinja2_ctrs/_upload_macros.html" import upload_assets, img_upload %}
{% from "jinja2_ctrs/_wangeditor_macro.html" import wangeditor_assets, wangeditor_editor %}

{{ upload_assets() }}
{{ wangeditor_assets() }}

<form method="post">
    {{ img_upload('cover', model.cover, '封面图', 120, 120) }}
    {{ wangeditor_editor('content', model.content, '400px', '请输入正文...') }}

    <button class="btn btn-primary" type="submit">保存</button>
</form>
{% endblock %}
```

---

## 五、开发一个新的宏

如果你发现某个 UI 组件在多处重复出现，可以把它封装成宏。

### 5.1 创建宏文件

在 `jinja2_ctrs/` 下新建文件，以下划线开头：

```
jinja2_ctrs/
├── _upload_macros.html       ← 上传组件
├── _wangeditor_macro.html    ← wangEditor 编辑器
├── _quill_macro.html         ← Quill 编辑器
└── _my_component.html        ← 你的宏文件（新建）
```

### 5.2 宏编写规范

```jinja
{# jinja2_ctrs/_my_component.html #}

{# 资源宏：加载 CSS/JS，全局只需一次 #}
{% macro my_assets() %}
{% if not g.get('_my_assets_rendered', False) %}
<link href="..." rel="stylesheet">
<script src="..."></script>
{% set _ = g.setdefault('_my_assets_rendered', True) %}
{% endif %}
{% endmacro %}


{# 组件宏：渲染 UI #}
{% macro my_input(name, value='', label='') %}
<div class="mb-3">
    <label>{{ label or name }}</label>
    <input name="{{ name }}" value="{{ value }}" class="form-control">
</div>
{% endmacro %}
```

**规范要点：**

1. 资源宏用 `g.setdefault('_xxx_rendered', True)` 去重，确保 JS/CSS 只加载一次
2. 组件宏**不直接访问**父模板的上下文变量（如 `model`），通过参数传值——这样不依赖 `with context`，随处可用
3. 参数建议使用 `name`（字段名）、`value`（当前值）、`show_name`（标签文字）的命名约定

---

## 六、宏文件清单

```
jinja2_ctrs/
├── _upload_macros.html
│   ├── upload_assets()
│   ├── img_upload(name, value, show_name, width, height)
│   ├── img_upload_multi(name, value, show_name, width, height)
│   ├── img_upload_path(name, value, show_name)
│   ├── file_upload(name, value, show_name)
│   └── file_upload_multi(name, value, show_name)
│
├── _wangeditor_macro.html
│   ├── wangeditor_assets()
│   └── wangeditor_editor(name, content, height, placeholder)
│
├── _quill_macro.html
│   ├── quill_assets()
│   └── quill_editor(name, content, height, placeholder, mode, enableImageUpload)
```