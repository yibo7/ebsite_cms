# 系统自带 API 文档

> 基础路径：`/api/`  
> 通用返回结构（JSON）：

```json
{
  "code": 0,        // 0=成功，-1=业务错误，401=无权限
  "msg": "succesful", // 提示信息
  "data": ...        // 具体数据（可选）
}
```

---

## 目录

- [通用工具](#1-通用工具)
- [内容获取](#2-内容获取)
- [分类与专题](#3-分类与专题)
- [文件上传](#4-文件上传)
- [用户交互（需登录）](#5-用户交互需登录)
- [内容发布（签名验证）](#6-内容发布签名验证)
- [乐谱相关（aitanqin 模块）](#7-乐谱相关)
- [积分相关](#8-积分相关)

---

## 1. 通用工具

### `GET /api/server_time`

获取服务器当前时间戳。

**返回示例：**

```json
{ "timestamp": 1726214400 }
```

### `GET /api/user_ip`

获取客户端的 IP 地址。

**返回示例：**

```json
{ "host": "192.168.1.100" }
```

---

## 2. 内容获取

### `GET|POST /api/content`

获取内容列表（最新 / 热门 / 推荐）。

| 参数    | 类型    | 必填 | 说明                                 |
|---------|---------|------|--------------------------------------|
| `cid`   | string  | 否   | 分类 ID，不传则获取全部分类          |
| `top`   | int     | 否   | 数量（默认 20，最大 1000）           |
| `type`  | int     | 否   | 1=最新（默认），2=热门，3=推荐       |

> 该接口缓存 2 秒。

**返回示例：**

```json
{
  "code": 0,
  "data": [
    {
      "_id": "6551e9f0b914f7b04a1201bc",
      "class_id": 15,
      "class_name": "流行",
      "id": 21,
      "info": "",
      "small_pic": "",
      "title": "真的爱你"
    }
  ]
}
```

### `GET|POST /api/content_pages`

获取分类下的分页内容。

| 参数      | 类型   | 必填 | 说明                |
|-----------|--------|------|---------------------|
| `cid`     | string | 是   | 分类 ID             |
| `pnumber` | int    | 否   | 页码（默认 1）      |

**返回示例：**

```json
{
  "code": 0,
  "count": 4,
  "data": [
    {
      "_id": "6552e81dd369ab19eeb9fd3d",
      "class_id": 15,
      "class_name": "流行",
      "id": 23,
      "info": "",
      "small_pic": "",
      "title": "真的爱你"
    }
  ]
}
```

### `GET|POST /api/content_details`

获取单条内容的完整详情。

| 参数 | 类型   | 必填 | 说明     |
|------|--------|------|----------|
| `id` | string | 是   | 内容 ID  |

**返回示例：**

```json
{
  "code": 0,
  "data": { "_id": "...", "title": "...", "info": "...", ... }
}
```

---

## 3. 分类与专题

### `GET|POST /api/category/`

获取分类列表（子级）。

| 参数  | 类型   | 必填 | 说明                        |
|-------|--------|------|-----------------------------|
| `pid` | string | 否   | 父级分类 ID，不传获取顶级分类 |

**返回示例：**

```json
{
  "code": 0,
  "data": [
    { "_id": "654f8e2d...", "class_name": "分类1", "id": 14 }
  ]
}
```

### `GET|POST /api/special`

获取专题列表。

| 参数  | 类型   | 必填 | 说明                          |
|-------|--------|------|-------------------------------|
| `pid` | string | 否   | 父级专题 ID，不传获取所有顶级专题 |

**返回示例：**

```json
{
  "code": 0,
  "data": [
    { "_id": "66b6048b...", "id": 1, "name": "流行", "img_src": "", "info": "" }
  ]
}
```

### `GET|POST /api/special_pages`

获取专题下的分页内容。

| 参数      | 类型   | 必填 | 说明        |
|-----------|--------|------|-------------|
| `sid`     | string | 是   | 专题 ID     |
| `pnumber` | int    | 否   | 页码（默认 1） |

**返回示例：**

```json
{
  "code": 0,
  "count": 4,
  "data": [ ... ]
}
```

### `POST /api/getsubmenus`

获取后台管理菜单树（两级）。

| 参数  | 类型   | 必填 | 说明      |
|-------|--------|------|-----------|
| `pid` | string | 否   | 父级菜单 ID |

**返回示例：**

```json
{
  "code": 0,
  "data": [
    {
      "MenuTitle": "系统管理",
      "img": "...",
      "Items": [
        { "ItemName": "用户管理", "url": "/admin/users", "img": "" }
      ]
    }
  ]
}
```

### `GET|POST /api/widget`

获取部件（Widget）渲染后的 HTML 代码。

| 参数  | 类型   | 必填 | 说明     |
|-------|--------|------|----------|
| `wid` | string | 否   | 部件 ID  |

**返回示例：**

```json
{ "code": 0, "data": "<div>...</div>", "msg": "succesful" }
```

---

## 4. 文件上传

### `POST /api/upfile`

上传文件（需管理员登录）。

| 参数     | 类型            | 必填 | 说明                                         |
|----------|-----------------|------|----------------------------------------------|
| `t`      | string (query)  | 否   | 上传类型：`ume`（编辑器）、`img`、`file`     |
| `upfile` | file (form)     | 是   | 文件（`t=ume` 时用此字段名）                 |
| `file`   | file (form)     | 是   | 文件（`t=img` 或 `t=file` 时用此字段名）     |

**限制：**

- 文件类型由后台 `upload_types` 配置控制
- 文件大小由后台 `upload_max_size` 配置控制（MB）

**返回示例：**

```json
{
  "originalName": "photo.jpg",
  "name": "photo.jpg",
  "url": "/api/upfile/xxx",
  "size": 102400,
  "state": "SUCCESS",
  "type": ".jpg"
}
```

### `GET /api/upfile/<filename>`

获取已上传的文件（MongoDB 存储模式）。缓存 10 分钟。

**返回：** 文件的二进制内容（mimetype 自动识别）

### `GET /api/uploads/<date>/<filename>`

获取已上传的文件（本地存储模式）。支持 `If-Modified-Since` 缓存协商。

| 参数     | 类型   | 必填 | 说明                 |
|----------|--------|------|----------------------|
| `date`   | path   | 是   | 上传日期，如 `20240914` |
| `filename` | path | 是   | 文件名               |

---

## 5. 用户交互（需登录）

> 这些接口需要在请求 header 中携带登录令牌（Token），通过 `api_blue_user` 蓝图统一验证。

### `POST /api/apply_credits`

申请积分（需后台审核）。频率限制：每小时 3 次。

| 参数      | 类型   | 必填 | 说明     |
|-----------|--------|------|----------|
| `credits` | int    | 否   | 申请数量 |
| `remark`  | string | 否   | 申请原因 |

### `POST|GET /api/login_info`

获取当前登录用户的信息。

```json
{
  "code": 0,
  "data": {
    "id": "66b31df8...",
    "name": "ebsite@163.com",
    "ni_name": "用户昵称",
    "group_id": "...",
    "avatar": "...",
    "open_id": "..."
  }
}
```

### `POST|GET /api/fav_content`

收藏 / 取消收藏内容（切换式）。频率限制：每分钟 3 次。

| 参数      | 类型   | 必填 | 说明                     |
|-----------|--------|------|--------------------------|
| `data_id` | string | 是   | 内容 ID                  |

- 如果未收藏则添加收藏，已收藏则取消收藏。

### `POST|GET /api/subscribe_user`

订阅 / 取消订阅制谱师（用户）。频率限制：每分钟 5 次。

| 参数      | 类型   | 必填 | 说明           |
|-----------|--------|------|----------------|
| `user_id` | string | 是   | 被订阅用户的 ID |

```json
{ "code": 0, "data": { "subscribed": true }, "msg": "订阅成功" }
```

### `GET /api/check_fav`

检查当前用户是否已收藏某内容。

| 参数      | 类型   | 必填 | 说明     |
|-----------|--------|------|----------|
| `data_id` | string | 是   | 内容 ID  |

```json
{ "code": 0, "data": { "favorited": true } }
```

### `GET /api/check_sub`

检查当前用户是否已订阅某制谱师。

| 参数      | 类型   | 必填 | 说明           |
|-----------|--------|------|----------------|
| `user_id` | string | 是   | 用户 ID        |

```json
{ "code": 0, "data": { "subscribed": false } }
```

### `POST /api/add_address`

添加 / 删除收货地址。

| 参数           | 类型   | 必填 | 说明                        |
|----------------|--------|------|-----------------------------|
| `data_id`      | string | 否   | 传入时删除此 ID 的地址      |
| `user_name`    | string | 否   | 收件人姓名（添加时）        |
| `phone`        | string | 否   | 手机号                      |
| `email`        | string | 否   | 邮箱                        |
| `post_code`    | string | 否   | 邮编                        |
| `address_info` | string | 否   | 详细地址                    |

---

## 6. 内容发布（签名验证）

### `POST /api/auto_post_content/<int:user_id>/<int:class_id>/<md5:site_key_md5>`

自动发布内容（通过网站密钥验证）。

- `user_id`：用户的整数 ID
- `class_id`：分类 ID
- `site_key_md5`：网站密钥 APP_KEY 的 MD5 值

**可 POST 的参数（字段白名单）：**

`title`, `info`, `small_pic`, `seo_title`, `seo_keyword`, `seo_description`, `column_1` ~ `column_21`（`column_5` 除外）

> `column_5`（乐谱路径）、`is_good`、`hits`、`user_id` 等敏感字段已从白名单移除。

**特殊字段：**

- `tagstr`：标签字符串，多个标签用英文逗号分隔（不能直接传 `tag`）

**调用示例：**

```
POST /api/auto_post_content/21/7/4224d63787d56b5a200bbfbc8eb8f3d9
Content-Type: application/x-www-form-urlencoded

title=我的标题&info=内容详情&tagstr=标签1,标签2
```

**返回示例：**

```json
{ "code": 0, "data": "发布成功", "msg": "succesful" }
```

### `GET|POST /api/get_content/<int:content_id>/<md5:site_key_md5>`

通过签名验证获取内容详情。

- `content_id`：内容的整数 ID
- `site_key_md5`：网站密钥 APP_KEY 的 MD5 值

| 参数     | 类型   | 必填 | 说明                                       |
|----------|--------|------|--------------------------------------------|
| `fields` | string | 否   | 逗号分隔的字段名列表，只返回这些字段       |

**返回示例：**

```json
{ "code": 0, "data": { "_id": "...", "title": "...", ... }, "msg": "succesful" }
```

### `POST /api/custom_form`

自定义表单提交。频率限制：每小时 3 次。

| 参数        | 类型   | 必填 | 说明                                    |
|-------------|--------|------|-----------------------------------------|
| `key`       | query  | 是   | 表单 Key，格式 `form_{form_id}`         |
| `safe_code` | body   | 否   | 验证码（表单开启了验证码时需要）        |
| 其他字段    | body   | 视表单定义 | 表单自定义字段                     |

---

## 7. 乐谱相关（aitanqin 模块）

> 基础路径：`/atq/api/`

### `POST|GET /atq/api/totab`

获取乐谱文件（原始二进制格式）。

| 参数 | 类型   | 必填 | 说明                   |
|------|--------|------|------------------------|
| `id` | string | 是   | 内容 ID（NewsContent._id） |

- 通过 `column_5` 字段定位乐谱文件路径
- 路径受安全校验保护，防止目录遍历

### `GET /atq/api/totab/<score_id>.js`

以 JS 格式获取乐谱文件（可被 CDN 缓存）。

- 返回自执行 JS 代码，将 base64 编码的乐谱注册到 `window.__cachedScores`
- 缓存控制：`Cache-Control: public, max-age=86400`

### `POST /atq/api/upload_score`

上传乐谱文件。频率限制：每分钟 5 次。

| 参数   | 类型       | 必填 | 说明                          |
|--------|------------|------|-------------------------------|
| `file` | file (form)| 是   | 乐谱文件（.gp 或 .musicxml） |

**返回示例：**

```json
{ "code": 0, "data": "/scores/new/a1b2c3d4.musicxml", "msg": "上传成功" }
```

### `GET /atq/api/check_score_hash`

检查乐谱文件哈希是否已存在（防重复上传）。

| 参数   | 类型   | 必填 | 说明                  |
|--------|--------|------|-----------------------|
| `hash` | string | 是   | 文件的 SHA-256 哈希值 |

```json
{ "code": 0, "data": { "exists": false }, "msg": "可以上传" }
```

---

## 8. 积分相关（credits_sys 模块）

> 基础路径：`/credits/api/`

### `GET|POST /credits/api/credits_plan`

获取积分套餐列表（无需登录）。

**返回示例：**

```json
{
  "code": 0,
  "data": [
    {
      "_id": "670134ea...",
      "credits": 1980,
      "ico_tag": "",
      "info": "可创作396首歌",
      "price": "498",
      "real_price": "198",
      "title": "交响精英版(不限时)"
    }
  ],
  "msg": "succesful"
}
```

### `POST /credits/api/buy_credits`

直接购买积分（需登录 Token）。

| 参数         | 类型   | 必填 | 说明                                                         |
|--------------|--------|------|--------------------------------------------------------------|
| `payment`    | int    | 是   | 支付方式：1=微信                                             |
| `price`      | number | 是   | 付款金额                                                     |
| `order_name` | string | 是   | 订单名称                                                     |
| `trade_type` | string | 否   | 微信支付类型：JSAPI / NATIVE / APP / MWEB / MICROPAY        |
| `openid`     | string | 否   | 微信 openid（payment=1 时必传）                              |

### `POST /credits/api/buy_credits_plan`

购买积分套餐（需登录 Token）。

| 参数         | 类型   | 必填 | 说明                                     |
|--------------|--------|------|------------------------------------------|
| `payment`    | int    | 是   | 支付方式：1=微信                         |
| `planid`     | string | 是   | 积分套餐 ID                              |
| `trade_type` | string | 否   | 微信支付类型（同 `buy_credits`）         |

### `GET|POST /credits/api/pay_notify/<payment_id>`

支付回调（微信/支付宝异步通知）。

| 参数         | 类型 | 必填 | 说明                     |
|--------------|------|------|--------------------------|
| `payment_id` | int  | 路径 | 1=微信，2=支付宝         |