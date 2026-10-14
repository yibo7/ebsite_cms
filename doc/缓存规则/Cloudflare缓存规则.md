# Cloudflare 缓存规则配置（EbSite CMS 多语言站）

适用前提：站点语言通过 URL 前缀区分，默认语言无前缀。

| URL | 语言 | 说明 |
|---|---|---|
| `/`、`/c112p1.html` | en | 默认语言，无前缀 |
| `/zh/`、`/zh/c112p1.html` | zh | 前缀 `/zh` |
| `/ja/`、`/ja/c112p1.html` | ja | 前缀 `/ja` |

---

## 一、前置检查（先做，否则规则配了也不生效）

Cloudflare 遇到下面两种情况会**拒绝缓存**，无论 Cache Rule 怎么写：

1. 响应带 `Set-Cookie`
2. 源站返回 `Cache-Control: no-cache` / `private` / `no-store`（仅当规则选了 "respect origin" 时）

用 curl 确认 HTML 页面是"干净"的：

```bash
curl.exe -sI https://你的域名/zh/c112p1.html | findstr /i "cache-control set-cookie cf-cache-status vary"
```

期望结果：

- **没有** `Set-Cookie`
- `Cache-Control` 不存在，或为 `public, max-age=...`

本项目已经为此做了设计（见 `index.py` 的 `ensure_session_id()` 与 `cms_page.py` 的 `/hit/<id>.gif` 信标）：页面响应不带 Cookie，登录态由 JS 异步填充，浏览量走独立信标。所以正常情况下应该是干净的。

若确实出现 `Set-Cookie`，先解决它，再谈缓存。

---

## 二、规则清单

Cloudflare Dashboard → 你的域名 → **Caching → Cache Rules → Create rule**。

> **重要语义**：Cache Rules 是叠加生效的，多个规则匹配同一请求时，**同一设置项以最后匹配的那条为准**；冲突设置（bypass 与 eligible）同样最后匹配的胜出。
> 因此本方案的规则顺序为：**通用缓存规则在上，特例（长缓存 / 排除）在下**。

| 顺序 | 规则名 | 作用 |
|---|---|---|
| 1 | 语言首页 | 缓存各语言首页 |
| 2 | 全部 .html 页面 | 缓存内容页 / 列表页 / 标签页 |
| 3（可选） | 内容页长缓存 | 给 `/a<id>.html` 更长 TTL |
| 4（可选） | 排除搜索页 | 让 `/search.html` 不吃缓存 |

---

## 三、规则 1：语言首页

**表达式**（推荐，面向未来新增语言）：

```
http.request.uri.path eq "/" or http.request.uri.path matches "^/[a-z]{2}/?$"
```

这条同时覆盖 `/`、`/zh`、`/zh/`、`/ja`、`/ja/`，将来加 `/ko/`、`/fr/` 无需改规则。

> 若你更希望白名单化、只匹配确定存在的语言，可换成：
> ```
> http.request.uri.path in {"/" "/zh" "/zh/" "/ja" "/ja/"}
> ```
> 代价是每加一种语言都要回来补一对（有无斜杠各一个）。

**设置**：

| 设置项 | 取值 | 原因 |
|---|---|---|
| Cache eligibility | **Eligible for cache** | |
| Edge TTL | **Ignore cache-control header and use this TTL** → `10 minutes` | 首页会随新内容变化，TTL 短一些 |
| Browser TTL | **Override origin** → `5 minutes` | 让访客较快看到更新 |
| Cache Key → Cache Deception Armor | **开启** | 防止 `/zh/a1.html/evil.css` 这类路径被当页面缓存 |
| Status Code TTL | 见下方"状态码 TTL" | |

---

## 四、规则 2：全部 .html 页面

**表达式**：

```
lower(http.request.uri.path.extension) in {"html" "htm"}
```

用 `extension` 字段而不是正则，天然对语言前缀无感——`/c112p1.html`、`/zh/c112p1.html`、`/ja/a126019.html` 全部命中，`/api/...`、`/user/...`、`/login`、`/hit/1.gif` 全部不命中。加 `lower()` 是为了兜住 `/A1.HTML` 这类大小写变体。

**设置**：

| 设置项 | 取值 |
|---|---|
| Cache eligibility | **Eligible for cache** |
| Edge TTL | **Ignore cache-control header and use this TTL** → `1 hour` |
| Browser TTL | **Override origin** → `5 minutes` |
| Cache Deception Armor | 开启 |
| Status Code TTL | 见下方 |

> 必须选 "Ignore cache-control header"：本项目的 HTML 响应**不带** `Cache-Control`，若选 "Use cache-control header if present, bypass cache if not"，Cloudflare 会直接绕过缓存，规则等于白配。

---

## 五、状态码 TTL（两条规则都要设）

Edge TTL 选了 "Ignore cache-control header" 之后，**所有状态码都会按同一个 TTL 缓存**，包括 404 和 500——内容被删或源站抽风时，错误页会被固化在边缘。必须单独约束：

| 状态码 | TTL | 说明 |
|---|---|---|
| 2xx | 沿用上面的 Edge TTL | 正常页面 |
| 301 / 302 | `30 minutes` | `/zh` → `/zh/` 的规范化跳转，缓存它是好事，但要留出调整余地 |
| 404 / 5xx | `0`（no-cache） | **务必设**，否则错误页会被缓存 |

---

## 六、可选规则 3：内容页长缓存

内容页 `/a<id>.html` 内容基本不变，可以吃更长的 TTL。因为"最后匹配者胜出"，这条要**放在规则 2 下面**：

```
http.request.uri.path matches "^/([a-z]{2}/)?a[0-9]+\.html$"
```

设置：Edge TTL = `1 day`，其余同上。

---

## 七、可选规则 4：排除搜索页

`/search.html?k=xxx` 会把每个关键词组合都变成一个缓存条目，容易把免费版缓存额度吃满，且搜索结果变化快。

因为 bypass 与 eligible 冲突时同样是"最后匹配者胜出"，这条独立的 Bypass 规则要**放在最下面**：

**表达式**：

```
http.request.uri.path in {"/search.html" "/zh/search.html" "/ja/search.html"}
```

**设置**：Cache eligibility = **Bypass cache**（其余项无需配置）。

这样规则 2 不用改动，靠顺序覆盖即可。

> 更省事的做法：不排除，但把规则 2 的 TTL 控制在 1 小时以内，搜索页自然不会陈旧太久。

---

## 八、为什么不需要额外的"排除动态页"规则

本项目里不该缓存的东西，恰好都不符合上面两条规则的表达式：

| 路径 | 是否命中规则 | 结果 |
|---|---|---|
| `/api/*` | 否 | 走默认行为（不缓存） |
| `/user/index`、`/user/favorite` | 否（无 .html） | 不缓存 ✅ |
| `/login`、`/reg` | 否 | 不缓存 ✅ |
| `/atq/post_data` | 否 | 不缓存 ✅ |
| `/hit/<id>.gif` | 否（gif） | 源站已设 `no-store` ✅ |
| `/imgcode` | 否 | 源站已设 `no-store` ✅ |
| `/admin/*` | 否 | 不缓存 ✅ |
| `/css/*`、`/js/*`、`/images/*` | 否 | 源站已设 `public, max-age=86400` ✅ |

所以这两条规则的表达式本身就是一道精确的白名单，不需要再补 Bypass 规则。唯一需要斟酌的灰色地带是搜索结果页，见第七节的可选规则 4。

> 提示：如果你的套餐在 Edge TTL 下方看不到 Status Code TTL 选项，就把 Edge TTL 整体调短（例如 10 分钟）作为兜底，避免错误页长期驻留边缘。

---

## 九、验证

```bash
curl.exe -sI https://你的域名/zh/c112p1.html | findstr /i "cf-cache-status age cache-control"
```

判读 `cf-cache-status`：

| 值 | 含义 |
|---|---|
| `MISS` → 再请求一次变 `HIT` | ✅ 配置成功 |
| `HIT` | ✅ 命中边缘缓存 |
| `DYNAMIC` | ❌ 规则没匹配上，或响应不可缓存（检查 Set-Cookie） |
| `BYPASS` | ❌ 被更高优先级的 bypass 规则或源站头挡住了 |

`age` 头会显示该响应在边缘缓存了多久。

对照检查语言首页与日文页：

```bash
curl.exe -sI https://你的域名/ | findstr /i cf-cache-status
curl.exe -sI https://你的域名/ja/c112p1.html | findstr /i cf-cache-status
```

再确认 404 没被缓存（请求一个不存在的页面两次，第二次仍应是 `cf-cache-status: MISS` 或 `DYNAMIC`，不能是 `HIT`）。

---

## 十、内容更新后的失效

Cloudflare 边缘缓存**不会**因为源站内部缓存失效而失效。本项目的列表页用 `list_ver:<class_id>` 换缓存 key（`website/pages/cms_page.py`），但 URL 没变，边缘仍会发旧页面。

三种做法，按投入递增：

**A. 靠 TTL 自然过期（零成本）**
Edge TTL 控制在 10 分钟 ~ 1 小时，内容更新最多延迟这么久。对内容站通常够用。

**B. 修改内容后主动 purge（推荐）**
在 `website/pages/cms_page.py` 的 `content_saved` 信号处理器里追加对 Cloudflare Purge API 的调用（需要 Zone ID 与一个 Cache Purge 权限的 API Token，放环境变量）：

```python
import os, requests

CF_ZONE = os.environ.get('CF_ZONE_ID')
CF_TOKEN = os.environ.get('CF_API_TOKEN')

def purge_cloudflare(urls):
    if not (CF_ZONE and CF_TOKEN and urls):
        return
    try:
        requests.post(
            f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE}/purge_cache',
            headers={'Authorization': f'Bearer {CF_TOKEN}'},
            json={'files': urls[:30]},   # 单次最多 30 个 URL
            timeout=5,
        )
    except Exception:
        pass   # 清理失败不影响主流程
```

建议顺带 purge 首页与所属分类页，因为它们会展示这条新内容：

```python
urls = [
    '/', '/zh/', '/ja/',
    f'/a{model.id}.html',
    f'/zh/a{model.id}.html',
    f'/ja/a{model.id}.html',
    f'/c{class_id}p1.html',        # 所属分类第一页
    f'/zh/c{class_id}p1.html',
    f'/ja/c{class_id}p1.html',
]
purge_cloudflare(urls)
```

注意：`/zh` 与 `/zh/` 是两个不同的缓存条目，只 purge 带斜杠的那个即可（无斜杠版会被 301 规范化）。

**C. Cache Tags（需 Enterprise）**
用 `Cache-Tag` 响应头 + 按标签清除。普通套餐不支持，不建议为此升级。

---

## 附：与本项目代码的对应关系

| 代码位置 | 与缓存的关系 |
|---|---|
| `index.py` `ensure_session_id()` | 页面响应不下发 cookie，保证可缓存 |
| `index.py` `set_static_cache_header()` | 静态资源补 `public, max-age=86400` |
| `index.py` `normalize_lang_prefix_slash()` | `/zh` → `/zh/` 301，消除重复 URL |
| `website/pages/cms_page.py` `/hit/<id>.gif` | 浏览量独立计数，内容页可整体缓存 |
| `website/themes/*/templates/base_site.html` | 输出 canonical / hreflang，决定搜索引擎如何理解多语言 |
