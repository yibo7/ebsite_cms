# 移动端 API 文档

> 基础路径：`/api/app/`  
> 通用返回结构（JSON）：

```json
{
  "code": 0,          // 0=成功，-1=业务错误，401=无权限
  "msg": "succesful",  // 提示信息
  "data": ...          // 具体数据（可选）
}
```

---

## 目录

- [图片验证码](#1-图片验证码)
- [短信/邮件验证码](#2-短信邮件验证码)
- [手机号登录/注册](#3-手机号登录注册)
- [密码登录/注册](#4-密码登录注册)
- [找回密码（三步）](#5-找回密码三步)
- [第三方登录](#6-第三方登录)
- [微信相关](#7-微信相关)
- [用户信息](#8-用户信息)
- [用户数据](#9-用户数据)
- [积分套餐](#10-积分套餐)
- [购买积分](#11-购买积分)
- [反馈与错误码](#12-反馈与错误码)

---

## 1. 图片验证码

### `POST /api/app/img_safe_code`

获取图片验证码。返回图片的 Base64 编码和一个 `code_key`，客户端在调用需要验证码的接口时传入两者。

**请求参数：** 无

**返回示例：**

```json
{
  "code": 0,
  "code_key": "ba595a00-2c99-49e6-9d82-f9ee52b2dec9",
  "img": "/9j/4AAQSkZJRgABAQAAAQABAAD..."
}
```

| 字段       | 类型   | 说明                               |
|------------|--------|------------------------------------|
| `code`     | int    | 0=成功                             |
| `code_key` | string | 验证码的 KEY，后续验证时需要传入   |
| `img`      | string | Base64 编码的 JPEG 图片            |

---

## 2. 短信/邮件验证码

### `POST /api/app/send_code`

发送手机短信或邮件验证码。

> 同一 IP 下，一小时内调用超过 3 次后，需要传入图片验证码。  
> 当返回 701 错误时，客户端应调用 `img_safe_code` 获取图片验证码后再重试。

**请求参数（JSON Body）：**

| 参数       | 类型   | 必填 | 说明                                                   |
|------------|--------|------|--------------------------------------------------------|
| `to`       | string | 是   | 手机号或 Email                                         |
| `code`     | string | 否   | 图片验证码（超出调用限制后需要传入）                   |
| `code_key` | string | 否   | 图片验证码的 KEY（超出调用限制后需要传入）             |

**返回示例：**

```json
{ "code": 0, "msg": "succesfull" }
```

---

## 3. 手机号登录/注册

### `POST /api/app/login_reg_mobile`

手机验证码登录。如果手机号不存在则自动注册，成功后返回 Token。

> 需要先调用 `send_code` 发送验证码，此接口会自动验证。

**请求参数（JSON Body）：**

| 参数      | 类型   | 必填 | 说明                   |
|-----------|--------|------|------------------------|
| `account` | string | 是   | 手机号                 |
| `code`    | string | 是   | 短信验证码             |

**返回示例：**

```json
{
  "code": 0,
  "data": "6f1a143f-b10b-4f6c-938a-b062fd581238",
  "msg": "openid"
}
```

| 字段   | 类型   | 说明                                               |
|--------|--------|----------------------------------------------------|
| `data` | string | 登录 Token，后续接口在 header 中通过 `x-api-key` 传入 |
| `msg`  | string | 绑定的三方平台 OpenID（如微信），无绑定则为空      |

---

## 4. 密码登录/注册

### `POST /api/app/reg_user_pass`

通过手机号 + 密码注册，成功后自动登录并返回 Token。

> 需要先调用 `send_code` 发送验证码。

**请求参数（JSON Body）：**

| 参数      | 类型   | 必填 | 说明           |
|-----------|--------|------|----------------|
| `account` | string | 是   | 手机号         |
| `pass`    | string | 是   | 密码           |
| `code`    | string | 是   | 短信验证码     |

**返回示例：**

```json
{
  "code": 0,
  "data": "c0b4d5ae-82cc-4950-a029-1d3bebbe506c",
  "msg": "succesful"
}
```

---

### `POST /api/app/login_pass`

通过手机号或邮箱 + 密码登录。

> 密码连续输错 3 次后需要传入图片验证码。

**请求参数（JSON Body）：**

| 参数        | 类型   | 必填 | 说明                                           |
|-------------|--------|------|------------------------------------------------|
| `account`   | string | 是   | 手机号或 Email                                 |
| `pass`      | string | 是   | 密码                                           |
| `code`      | string | 否   | 图片验证码（1 小时内超过 3 次错误后需要）      |
| `code_key`  | string | 否   | 图片验证码的 KEY                               |

**返回示例（成功）：**

```json
{
  "code": 0,
  "data": "c0b4d5ae-82cc-4950-a029-1d3bebbe506c",
  "msg": "succesful"
}
```

**返回示例（失败）：**

```json
{ "code": -1, "msg": "用户名或密码错误" }
```

**返回示例（需要图片验证码）：**

```json
{ "code": 401, "data": null, "msg": "请传入code_key与code" }
```

---

## 5. 找回密码（三步）

### 步骤 1：`POST /api/app/find_pass1`

输入账号（手机号），获取找回密码的 `pass_key`。

> 频率限制：24 小时内只能请求 10 次。

**请求参数（JSON Body）：**

| 参数      | 类型   | 必填 | 说明           |
|-----------|--------|------|----------------|
| `account` | string | 是   | 手机号或 Email |

**返回示例：**

```json
{
  "code": 0,
  "data": "find_7cc9a7a8-6910-46f9-9137-b4f04c34ccbd",
  "msg": "请在1分钟内完成下一步!"
}
```

| 字段   | 类型   | 说明                              |
|--------|--------|-----------------------------------|
| `data` | string | 找回密码的临时 Key，有效期为 1 分钟 |

---

### 步骤 2：`POST /api/app/find_pass2`

验证手机验证码。

> 需要先调用 `send_code` 发送验证码。  
> 先调用 `find_pass1` 获取 `pass_key`。

**请求参数（JSON Body）：**

| 参数       | 类型   | 必填 | 说明             |
|------------|--------|------|------------------|
| `pass_key` | string | 是   | 步骤 1 获取的 Key |
| `account`  | string | 是   | 手机号           |
| `code`     | string | 是   | 短信验证码       |

**返回示例：**

```json
{
  "code": 0,
  "data": "find_7cc9a7a8-...",
  "msg": "验证码正确，请在5分钟内完成密码的修改!"
}
```

---

### 步骤 3：`POST /api/app/find_pass3`

设置新密码。

**请求参数（JSON Body）：**

| 参数       | 类型   | 必填 | 说明                           |
|------------|--------|------|--------------------------------|
| `pass_key` | string | 是   | 步骤 2 获取的 Key（有效期 5 分钟） |
| `newpass`  | string | 是   | 新密码                         |

**返回示例：**

```json
{ "code": 0, "data": "", "msg": "succesful" }
```

---

## 6. 第三方登录

### `POST /api/app/wx_login`

微信授权登录（小程序 / App）。通过 `wx.login()` 获取的 `code` 换取 `openid`，自动注册或登录。

**请求参数（JSON Body）：**

| 参数       | 类型   | 必填 | 说明                                              |
|------------|--------|------|---------------------------------------------------|
| `wxcode`   | string | 是   | 通过 `wx.login()` 或 `uni.login()` 获取的 code    |
| `nickname` | string | 否   | 微信昵称（通过 `wx.getUserProfile` 获取）         |
| `avatar`   | string | 否   | 头像 URL                                          |
| `mobile`   | string | 否   | 手机号（通过 `getPhoneNumber` 获取）              |

**返回示例：**

```json
{
  "code": 0,
  "data": "fwf45wf5ghe5tere464wf",
  "msg": "succesful"
}
```

---

### `POST /api/app/openlogin`

获取第三方登录的连接 URL（通过插件机制）。

| 参数  | 类型   | 必填 | 说明            |
|-------|--------|------|-----------------|
| `pid` | string | 是   | 登录插件 ID     |

**返回示例：**

```json
{ "code": 0, "data": "https://open.weixin.qq.com/...", "msg": "succesful" }
```

---

## 7. 微信相关

### `POST /api/app/bind_wx`

绑定微信账号到当前登录用户。

> 需在 Header 中携带 `x-api-key`（登录 Token）。

**请求参数（JSON Body）：**

| 参数       | 类型   | 必填 | 说明                                            |
|------------|--------|------|-------------------------------------------------|
| `wxcode`   | string | 是   | `wx.login()` 获取的 code                        |
| `nickname` | string | 否   | 微信昵称                                        |
| `avatar`   | string | 否   | 头像 URL                                        |
| `mobile`   | string | 否   | 手机号                                          |

**返回示例：**

```json
{
  "code": 0,
  "data": "新的登录Token（包含openid信息）",
  "msg": "succesful"
}
```

---

### `GET /api/app/query_order`

查询微信支付订单状态。

| 参数      | 类型   | 必填 | 说明           |
|-----------|--------|------|----------------|
| `orderid` | string | 是   | 微信订单号     |

**返回示例：**

```json
{ "code": 0, "data": { "trade_state": "SUCCESS", ... }, "msg": "succesful" }
```

---

## 8. 用户信息

> 以下接口需在请求 Header 中携带 `x-api-key`（登录后返回的 Token），除非特别说明。

### `POST /api/app/userinfo`

获取当前登录用户的详细信息。

**请求参数：** 无

**返回示例：**

```json
{
  "code": 0,
  "data": {
    "_id": "66b31df8d56c2ba2bf16099f",
    "avatar": "/images/default_avatar.png",
    "credits": 0,
    "email_address": "ebsite@163.com",
    "group_id": "64c38c2ccccb3a9a6f8b24a4",
    "group_name": "1个月VIP",
    "id": 3,
    "last_login_date": 1723014647.941981,
    "mobile_number": "15910983264",
    "ni_name": "cqs",
    "username": "ebsite@163.com"
  },
  "msg": "succesful"
}
```

| 字段             | 类型    | 说明           |
|------------------|---------|----------------|
| `_id`            | string  | 用户唯一 ID    |
| `username`       | string  | 用户账号       |
| `ni_name`        | string  | 用户昵称       |
| `avatar`         | string  | 头像 URL       |
| `credits`        | int     | 可用积分       |
| `group_id`       | string  | 用户组 ID      |
| `group_name`     | string  | 用户组名称     |
| `mobile_number`  | string  | 手机号         |
| `email_address`  | string  | 邮箱           |
| `id`            | int     | 数字编号       |
| `last_login_date`| number | 最后登录时间戳 |

---

### `POST /api/app/user_groups`

获取所有用户组（含 VIP 类型）。

**返回示例：**

```json
{ "code": 0, "data": [ ... ], "msg": "succesful" }
```

---

### `POST /api/app/update_avatar`

修改用户头像。上传图片文件，最大 1MB。

| 参数   | 类型       | 必填 | 说明     |
|--------|------------|------|----------|
| `file` | file (form)| 是   | 头像图片 |

---

### `POST /api/app/update_niname`

修改用户昵称。

| 参数       | 类型   | 必填 | 说明       |
|------------|--------|------|------------|
| `new_name` | string | 是   | 新昵称     |

---

### `POST /api/app/logout`

退出登录（清除服务端 Token）。

**请求参数：** 无（需 Header 中携带 `x-api-key`）

**返回示例：**

```json
{ "code": 0, "data": "", "msg": "succesful" }
```

---

## 9. 用户数据

### `POST /api/app/my_data`

获取当前登录用户发布的内容列表（分页）。

> 需登录 Token。

| 参数       | 类型   | 必填 | 说明             |
|------------|--------|------|------------------|
| `pnumber`  | int    | 否   | 页码（默认 1）   |

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

---

### `POST|GET /api/app/user_data`

获取指定用户发布的内容列表（分页）。

> 无需登录。

| 参数       | 类型   | 必填 | 说明                |
|------------|--------|------|---------------------|
| `uid`      | string | 否   | 指定用户的 ID       |
| `pnumber`  | int    | 否   | 页码（默认 1）      |

---

## 10. 积分套餐

### `GET|POST /credits/api/credits_plan`

获取积分套餐列表（无需登录）。

**返回示例：**

```json
{
  "code": 0,
  "data": [
    {
      "_id": "670134ea1225a9d60e8b781d",
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

| 字段          | 类型   | 说明       |
|---------------|--------|------------|
| `_id`         | string | 套餐 ID    |
| `title`       | string | 套餐标题   |
| `credits`     | int    | 可得积分   |
| `price`       | string | 原价       |
| `real_price`  | string | 实际价格   |
| `info`        | string | 套餐简介   |
| `ico_tag`     | string | 图标代码   |

---

## 11. 购买积分

### `POST /credits/api/buy_credits`

直接购买积分。需登录 Token。

**请求参数（JSON Body）：**

| 参数         | 类型   | 必填 | 说明                                                      |
|--------------|--------|------|-----------------------------------------------------------|
| `payment`    | int    | 是   | 支付方式：1=微信                                          |
| `price`      | number | 是   | 付款金额                                                  |
| `order_name` | string | 是   | 订单名称                                                  |
| `trade_type` | string | 否   | 微信支付类型：JSAPI / NATIVE / APP / MWEB / MICROPAY     |
| `openid`     | string | 否   | 微信 openid（payment=1 时推荐传入，否则用 Token 中的 openid） |

**返回示例：**

```json
{
  "code": 0,
  "data": {
    "_id": "66f94a7a8dc28ee89706efc4",
    "_price": 0.01,
    "_real_price": 0.01,
    "add_credits": 1,
    "info": "购买积分【购买创作积分】",
    "is_complete": false,
    "is_payed": false,
    "order_name": "购买创作积分",
    "pay_type": 1,
    "payment_prams": {
      "appId": "wx7261621a054cff30",
      "nonceStr": "L5gW25atR0h75sLR",
      "package": "prepay_id=wx2920392289707289...",
      "paySign": "E3C1BA6B4A56FC94CE8071A126ABCC0B",
      "signType": "MD5",
      "timeStamp": "1727613562"
    },
    "user_id": "66c9b019e9950cc65dffa982"
  },
  "msg": "succesful"
}
```

| 字段            | 类型    | 说明                         |
|-----------------|---------|------------------------------|
| `_id`           | string  | 订单 ID                      |
| `_price`        | number  | 原价                         |
| `_real_price`   | number  | 实际支付价格                 |
| `add_credits`   | int     | 此订单可获得的积分           |
| `payment_prams` | object  | 微信支付调起参数（前端凭此调起支付） |
| `is_complete`   | boolean | 是否完成                     |
| `is_payed`      | boolean | 是否已支付                   |

---

### `POST /credits/api/buy_credits_plan`

购买积分套餐。需登录 Token。

**请求参数（JSON Body）：**

| 参数         | 类型   | 必填 | 说明                                                 |
|--------------|--------|------|------------------------------------------------------|
| `payment`    | int    | 是   | 支付方式：1=微信                                     |
| `planid`     | string | 是   | 积分套餐 ID（从 `credits_plan` 接口获取）            |
| `trade_type` | string | 否   | 微信支付类型（JSAPI / NATIVE / APP / MWEB / MICROPAY） |

**返回示例：** 同 `buy_credits`。

---

### `GET|POST /credits/api/pay_notify/<payment_id>`

支付回调（微信/支付宝异步通知，仅用于服务端）。

> 客户端无需调用此接口。

| 参数         | 类型 | 必填 | 说明               |
|--------------|------|------|--------------------|
| `payment_id` | int  | 路径 | 1=微信，2=支付宝   |

---

## 12. 反馈与错误码

### 通用错误码

| `code` | 说明                       |
|--------|----------------------------|
| 0      | 成功                       |
| -1     | 业务错误（参考 `msg` 字段）|
| 401    | 无权限 / 需要验证码        |
| 701    | 需要图片验证码             |

### 各接口频率限制

| 接口                          | 限制                          |
|-------------------------------|-------------------------------|
| `send_code`                   | 1 小时内 3 次（IP）           |
| `find_pass1`                  | 24 小时内 10 次（IP）         |
| `login_pass`                  | 3 次错误后需图片验证码        |
| `buy_credits` / `buy_credits_plan` | 由微信支付风控控制        |

---

> 完整 API 文档也可在 Apifox 查看：https://app.apifox.com/project/4969772