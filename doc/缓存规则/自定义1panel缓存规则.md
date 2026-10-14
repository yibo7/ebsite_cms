# 关于 1Panel 缓存规则

## 为什么需要自定义缓存

1Panel 的反向代理缓存默认生成一条 `location ^~ /` 规则，匹配**所有路径**，并配合 `proxy_ignore_headers Set-Cookie Cache-Control expires;` 强制忽略源站的“禁止缓存”信号。这意味着：

- **所有 GET 请求**，只要后端返回 200/304/301/302，都会被 Nginx 缓存 10 天。
- **个人后台、注册、登录、API 等敏感页面**同样被缓存，且缓存 key 不区分用户身份。
- 后果是 **A 用户访问后台后，B 用户可能看到 A 的缓存内容**，造成数据泄露。

1Panel 面板不提供细粒度规则设置，无法通过 UI 指定“只缓存哪些路径”。因此，**必须手动编辑 Nginx 配置**，把缓存范围精确限定在需要的页面上，同时将后台等敏感路径排除在外。这就是需要自定义缓存的原因。

---

## 一、1Panel 缓存配置的两个入口

1Panel 中与缓存相关的设置分布在两处：

| 位置 | 设置项 | 对应 Nginx 指令 | 实际作用 |
|:---|:---|:---|:---|
| 反代缓存页面 | 缓存空间限制 | `max_size` | 缓存文件总大小上限 |
| 反代缓存页面 | 缓存计数内存大小 | `keys_zone` | 缓存键的内存大小 |
| 反代缓存页面 | 缓存过期时间 | `inactive` | 缓存文件多久没人访问就删除 |
| 高级设置 | 服务器缓存时间 | `proxy_cache_valid` | Nginx 缓存后端响应的有效期 |
| 高级设置 | 浏览器缓存时间 | `expires` | 用户浏览器本地缓存时长 |

**核心区分**：
- **服务器缓存** = Nginx 自身缓存后端数据，减少回源。
- **浏览器缓存** = 通过 `expires` 头告诉浏览器缓存多久。

---

## 二、1Panel 默认缓存配置的问题

1Panel 默认生成的反代缓存配置类似：

```nginx
location ^~ / {
    proxy_pass http://fzjh;
    proxy_set_header Host $host;
    # ... 其他 proxy_set_header
    proxy_ignore_headers Set-Cookie Cache-Control expires;
    proxy_cache proxy_cache_zone_of_www.aitanqin.com;
    proxy_cache_key $host$uri$is_args$args;
    proxy_cache_valid 200 304 301 302 10d;
    if ( $uri ~* "\.(gif|png|jpg|css|js|woff|woff2|jpeg|svg|webp|avif)$" ) {
        expires 4h;
    }
}
```

### 问题 1：缓存范围覆盖所有路径

`location ^~ /` 匹配**所有路径**，包括后台、注册、登录、API 等敏感页面。

### 问题 2：`proxy_ignore_headers Set-Cookie` 强制缓存

正常情况下，Nginx 看到响应带 `Set-Cookie` 或 `Cache-Control: no-cache` 会拒绝缓存。但这行指令让 Nginx **无视这些信号**，强行缓存，导致用户私有数据被缓存。

### 问题 3：缓存 key 不区分用户

`proxy_cache_key $host$uri$is_args$args` 不包含 cookie 或用户身份。所有用户访问同一 URL 命中同一份缓存。

### 问题 4：1Panel 面板不提供细粒度规则设置

1Panel 把缓存简化为一个开关，无法通过 UI 配置“只缓存哪些路径”。要实现精细化控制，必须**手动编辑 Nginx 配置文件**。

---

## 三、解决方案：拆分 location 实现精细化缓存

### 目标

只缓存以下三类路径，其余路径（后台、API、注册等）不缓存：

1. `.html` / `.htm` 文件
2. 首页 `/`
3. 语言目录（`/zh/`、`/ja/`、`/en/` 等）

### 完整配置

```nginx
# 1. 缓存 .html / .htm 文件
location ~* \.(html|htm)$ {
    proxy_pass http://fzjh;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_http_version 1.1;
    add_header X-Cache $upstream_cache_status;
    proxy_ssl_server_name off;
    proxy_ssl_name $proxy_host;
    proxy_ignore_headers Set-Cookie Cache-Control expires;
    proxy_cache proxy_cache_zone_of_www.aitanqin.com;
    proxy_cache_key $host$uri$is_args$args;
    proxy_cache_valid 200 304 301 302 10d;
}

# 2. 缓存首页
location = / {
    proxy_pass http://fzjh;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_http_version 1.1;
    add_header X-Cache $upstream_cache_status;
    proxy_ssl_server_name off;
    proxy_ssl_name $proxy_host;
    proxy_ignore_headers Set-Cookie Cache-Control expires;
    proxy_cache proxy_cache_zone_of_www.aitanqin.com;
    proxy_cache_key $host$uri$is_args$args;
    proxy_cache_valid 200 304 301 302 10d;
}

# 3. 缓存语言目录
location ~ ^/(zh|ja|en|ar|bg|cs|da|de|el|es|fa|fi|fr|he|hi|hu|id|it|ko|ms|nl|no|pl|pt|ro|ru|sk|sv|th|tr|uk|vi)/?$ {
    proxy_pass http://fzjh;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_http_version 1.1;
    add_header X-Cache $upstream_cache_status;
    proxy_ssl_server_name off;
    proxy_ssl_name $proxy_host;
    proxy_ignore_headers Set-Cookie Cache-Control expires;
    proxy_cache proxy_cache_zone_of_www.aitanqin.com;
    proxy_cache_key $host$uri$is_args$args;
    proxy_cache_valid 200 304 301 302 10d;
}

# 4. 其他所有路径（后台、API、注册等）——不缓存
location / {
    proxy_pass http://fzjh;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_http_version 1.1;
    proxy_ssl_server_name off;
    proxy_ssl_name $proxy_host;
    proxy_cache off;
}
```

### 匹配优先级说明

Nginx location 匹配顺序：`=` (精确) > `^~` (前缀) > `~`/`~*` (正则) > `/` (默认)

1. `location = /` 精确匹配首页。
2. `location ~* \.(html|htm)$` 正则匹配 HTML 文件。
3. `location ~ ^/(zh|ja|...)/?$` 正则匹配语言目录。
4. `location /` 兜底，其他所有路径不缓存。

---

## 四、缓存 zone 的全局定义

在站点配置的 `server` 块之外，还有一行定义缓存 zone 的指令：

```nginx
proxy_cache_path /www/sites/www.aitanqin.com/cache levels=1:2 keys_zone=proxy_cache_zone_of_www.aitanqin.com:5m max_size=10g inactive=30d;
```

| 参数 | 值 | 作用 |
|:---|:---|:---|
| `keys_zone` | 5m | 缓存键内存大小 |
| `max_size` | 10g | 缓存文件总大小上限 |
| `inactive` | 30d | 缓存文件 30 天没人访问就删除 |

**注意**：`inactive` 应大于 `proxy_cache_valid`，否则缓存文件可能在有效期内被提前清理。

---

## 五、Cloudflare 与 Nginx 两层缓存的关系

```
用户浏览器
   │
   ├─ Cloudflare 边缘缓存（Cache Rule 决定缓存资格）
   │      │
   │      └─ 回源到 Nginx
   │             │
   │             └─ Nginx 反代缓存（proxy_cache_valid 10d）
   │                    │
   │                    └─ 回源到后端应用
```

- **Cloudflare 层**：由 Cache Rule 控制，命中时响应头出现 `cf-cache-status: HIT`。
- **Nginx 层**：由 `proxy_cache_valid` 控制，命中时响应头出现 `X-Cache: HIT`。

### 验证方法

访问页面后查看响应头：

| 响应头组合 | 含义 |
|:---|:---|
| `cf-cache-status: HIT` | Cloudflare 命中缓存，请求未到 Nginx |
| `cf-cache-status: MISS` + `X-Cache: HIT` | Cloudflare 未缓存，Nginx 命中缓存 |
| `cf-cache-status: MISS` + `X-Cache: MISS` | 两层都未缓存，打到后端 |

---

## 六、Cloudflare Cache Rule 参考

与 Nginx 配置对应的 Cloudflare Cache Rule 表达式：

```
(http.request.uri.path.extension in {"html" "htm"})
or (http.request.uri.path eq "/")
or (
  http.request.uri.path in {
    "/zh/" "/ja/" "/en/" "/ar/" "/bg/" "/cs/" "/da/" "/de/" "/el/" "/es/"
    "/fa/" "/fi/" "/fr/" "/he/" "/hi/" "/hu/" "/id/" "/it/" "/ko/" "/ms/"
    "/nl/" "/no/" "/pl/" "/pt/" "/ro/" "/ru/" "/sk/" "/sv/" "/th/" "/tr/"
    "/uk/" "/vi/"
  }
)
```

**注意**：Cloudflare 免费版不支持 `matches`（正则）操作符，需使用 `in` 白名单。

---

## 七、关键注意事项

1. **`proxy_ignore_headers Set-Cookie` 是危险指令**：它让 Nginx 无视源站的“禁止缓存”信号，强行缓存。只应对确实不含用户私有数据的页面使用。
2. **后台、注册、登录等路径必须排除**：这些页面含用户身份信息，一旦被缓存会导致数据泄露。
3. **语言目录白名单按实际支持的语言维护**：不要盲目添加所有两字母代码，`/reg`、`/api` 等路径可能被误伤。
4. **`inactive` 应大于 `proxy_cache_valid`**：否则缓存文件可能在有效期内被提前清理。
5. **修改配置后需测试**：`nginx -t` 检查语法，然后 reload。

---

## 八、操作步骤

1. 进入 **1Panel → 网站 → 你的站点 → 反向代理 → 编辑**
2. 找到生成的配置文件（通常在 `/www/sites/www.aitanqin.com/proxy/` 目录下）
3. 按上述方案替换 `location` 块
4. 保存后执行 `nginx -t` 测试
5. 重载 Nginx：`nginx -s reload` 或通过 1Panel 面板重启
6. 访问各路径，检查响应头中的 `X-Cache` 和 `cf-cache-status` 确认缓存行为符合预期