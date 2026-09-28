# AI 购物系统使用与开发文档

> 模块路径：`eb_modules/ai_cart/`
>
> 前台入口：`/ai_cart/ask/index.html`
>
> 后台入口：网站后台 → 模块管理 → 智能询价系统
>
> **⚠ 依赖声明：本模块强依赖 `eb_shop`（商城模块），不可单独启用。**

---

## 一、系统架构

### 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                     ai_cart（AI 购物模块）                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  自身职责：AI 对话 + 商品搜索 + 产品卡片展示            │      │
│  │  ─────────────────────────────────────────              │      │
│  │  • 欢迎语 / 聊天 API                                   │      │
│  │  • 品类处理器（搜索逻辑）                               │      │
│  │  • 后台提示词配置                                      │      │
│  │  • 前台聊天界面 + 购物车侧栏                           │      │
│  └────────────────────┬───────────────────────────────────┘      │
│                       │ 依赖                                    │
│                       ▼                                          │
│  ┌────────────────────────────────────────────────────────┐      │
│  │              eb_shop（商城模块）                         │      │
│  │  ─────────────────────────────────────────              │      │
│  │  • 购物车 API（加购/列表/改数量/删除）                  │      │
│  │  • 商品数据（NewsContent）                             │      │
│  │  • 价格计算（阶梯价 / 会员价）                          │      │
│  │  • 订单 / 结算 / 支付                                  │      │
│  └────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户浏览器                             后端
  │                                     │
  │  ┌──────────────── ai_cart 模块 ────────────┐
  │  │  POST /api/quote/chat                    │  AI 对话 + 搜索商品
  │  │  ◄── 返回产品卡片（含 id + product_id）  │
  │  └──────────────────────────────────────────┘
  │                                     │
  │  ┌─────────── eb_shop 模块 ─────────────────┐
  │  │  POST /shop/api/cart/add                │  加购（复用商城购物车）
  │  │  GET  /shop/api/cart/items              │  读取购物车列表
  │  │  POST /shop/api/cart/update             │  修改数量
  │  │  POST /shop/api/cart/remove             │  删除商品
  │  │  ◄── 购物车数据全部存 ShoppingCartBll   │
  │  └──────────────────────────────────────────┘
  │                                     │
  │  点击「去购物车结算」                           │
  │  ─────────────────────                    │
  │  window.location.href = '/shop/cart'       │  跳转商城购物车页面
  │                                     │
  │  (后续：提交订单 → 支付 → 订单管理，全部走商城流程)
```

**关键设计原则：** `ai_cart` 只做 AI 对话推荐这一个事，购物车存储、价格计算、订单结算全部委托给 `eb_shop`，不重复实现。

### 核心模块文件

| 文件 | 模块 | 职责 |
|------|------|------|
| `__init__.py` | ai_cart | 模块入口、蓝图注册、动态品类下拉 |
| `ai_cart_apis.py` | ai_cart | AI 聊天 API（欢迎语 + 对话） |
| `ai_cart_pages.py` | ai_cart | 首页重定向 + 后台提示词配置 |
| `ai_handlers/` | ai_cart | 品类处理器（搜索逻辑） |
| `datas/prompts_config.py` | ai_cart | 提示词配置数据模型 |
| `templates/prompts_config.html` | ai_cart | 提示词配置后台页面 |
| `static/ask/index.html` | ai_cart | AI 聊天前台页面 |
| `static/ask/js/app.js` | ai_cart | 前端逻辑（聊天 + 购物车侧栏） |
| `shop_apis.py`（cart/*） | **eb_shop** | ⚠ 购物车全部 API（被 ai_cart 调用） |
| `datas/cart_manger.py` | **eb_shop** | ⚠ 购物车核心业务逻辑 |
| `datas/shopping_cart.py` | **eb_shop** | ⚠ 购物车数据模型 |
| `shop_pages.py`（/cart） | **eb_shop** | ⚠ 购物车页面 + 结算流程 |

### 为什么 ai_cart 不能单独运行

| 功能 | 实现在 | 原因 |
|------|--------|------|
| 商品数据 | `eb_shop` 的 `NewsContent` | AI 搜索依赖商城商品 |
| 购物车存储 | `eb_shop` 的 `ShoppingCartBll` | 购物车是商城核心能力 |
| 价格计算 | `eb_shop` 的 `CartManager` | 阶梯价/会员价/零售价由商城定价引擎负责 |
| 订单结算 | `eb_shop` 的 `/post_order` + 支付 | 完整的电商交易流程 |
| 购物车页面 | `eb_shop` 的 `/shop/cart` | 最终结算入口 |

### 依赖的外部模块（eb_shop）

购物车相关功能全部复用商城模块的 API，不重复实现：

| API | 路径 | 用途 |
|-----|------|------|
| 加购 | `POST /shop/api/cart/add` | AI 侧栏点击 [+] 调用 |
| 列表 | `GET /shop/api/cart/items` | 渲染右侧"已选商品"面板 |
| 改数量 | `POST /shop/api/cart/update` | 修改购物车商品数量 |
| 删除 | `POST /shop/api/cart/remove` | 从购物车移除商品 |
| 清空 | `POST /shop/api/cart/clear` | 清空购物车 |
| 结算 | `/shop/cart` | 跳转到商城购物车页面提交订单 |

> 所有购物车 API 均支持游客模式（`cart_token` cookie）和登录模式。

---

## 二、系统使用

### 2.1 后台配置

#### AI 提供者配置（系统级）

AI 提供者已迁移至系统级插件管理，配置分两步：

**① 系统设置 → 选择默认 AI 提供者**

路径：网站后台 → 系统设置 → AI 提供者

| 字段 | 说明 |
|------|------|
| AI 提供者 | 下拉选择已安装的 AI 插件（DeepSeek / 阿里千问 / OpenAI / 京东JoyAgent） |

**② 插件管理 → 配置 API 密钥**

路径：网站后台 → 插件管理 → AI 提供者 → 点击对应插件

| 字段 | 说明 |
|------|------|
| API Key | 对应供应商的 API 密钥 |
| 模型名称 | 如 `deepseek-chat`、`qwen-plus`、`gpt-4o-mini` |

> 切换 AI 提供者后立即生效，无需重启。

#### 品类选择

| 选项 | 说明 |
|------|------|
| 打印复印耗材 | 按品牌+型号精确搜索（适用于鼓芯、粉盒） |
| 服装 | 按品类+颜色+尺码关键词模糊搜索（示例） |

> 切换品类后**需要重启项目**才能生效。

#### 购物车模式设置

在商城模块配置中可控制购物车是否需要登录：

**路径：网站后台 → 模块管理 → eb_shop 商城系统 → 购物车设置**

| 选项 | 行为 |
|------|------|
| 购物车必须登录才能访问（勾选）| 未登录用户无法加购，跳转登录页 |
| 不勾选 | 游客可加购（`cart_token` 存 cookie），结算时要求登录 |

### 2.2 提示词配置

> 路径：AI 模块配置 → 提示词配置

允许管理员在不修改代码、不重启的情况下编辑 AI 的提示词：

| 配置项 | 用途 |
|--------|------|
| 店铺名称 | AI 文案中自称的名称 |
| 欢迎语 | 客户打开对话框时显示的欢迎消息（支持 HTML） |
| 提取提示词 | 指导 AI 从用户消息中提取产品参数 |
| 销售文案模板 | AI 撰写回复时使用的模板 |
| 引导提示词 | AI 无法提取参数时引导用户提供更多信息 |

> 修改提示词后**无需重启**，刷新页面即可生效。

### 2.3 前端使用

**前台地址：** `http://your-site/ai_cart/ask/index.html`

**基本流程：**
1. 用户在左侧对话框输入需求（如 "Ricoh MPC8003 鼓芯多少钱"）
2. AI 提取参数 → 搜索数据库 → 返回匹配产品（卡片形式）
3. 用户点击产品卡片上的 `[+]` 加入购物车
4. 右侧"已选商品"面板自动更新，显示价格、阶梯价提示
5. 点击"去购物车结算"跳转到商城购物车页面
6. 登录后提交订单、支付（完全复用商城流程）

**支持的搜索方式：**
- 品牌 + 型号：`"Ricoh MPC8003"`
- 仅品牌：`"佳能鼓芯有哪些"`
- 仅型号：`"MPC8003"`
- OEM/SKU/料号：`"GX-C200-037"`
- 完整描述：`"Drum Unit for Ricoh MP 9000"`

**产品卡片功能：**
- 缩略图 → 点击在新窗口打开商品详情页
- 商品名称 → 点击在新窗口打开商品详情页
- 价格显示 → 显示当前用户的成交价（已含阶梯/会员折扣），原价带删除线对比
- `[+]` 按钮 → 调用购物车 API 加购，按钮变为 `✓`

**右侧购物车面板功能：**
- 显示已选商品列表（缩略图、名称、SKU、价格、数量）
- 价格来源标签（会员价 / 阶梯价 / 零售价）
- 阶梯价提示（"再买 X 件可享批发价 ¥Y"）
- 数量 +/- 按钮，实时同步后端
- 底部汇总：商品款数、总数量、原价合计、优惠折扣、报价合计
- "去购物车结算"按钮

---

## 三、API 文档

### 3.1 AI 模块 API

Base URL：`/ai_cart/api/quote/`

#### 获取欢迎语

```
GET /welcome
→ { "welcome": "...", "shop_name": "..." }
```

#### AI 聊天

```
POST /chat
{
    "messages": [
        { "role": "user", "content": "佳能 IR1730 多少钱" }
    ]
}
→ {
    "reply": "HTML 格式回复",
    "matches": [
        {
            "id": "MongoDB _id",
            "title": "佳能 IR1730 鼓芯",
            "small_pic": "...",
            "unit_price": 20.0,
            "market_price": 25.0,
            "class_name": "标准",
            "sku": "GX-C200-037",
            "product_id": "规格的 productId",
            "url": "...",
            "qty": 1
        }
    ]
}
```

`matches` 数组中的字段说明：

| 字段 | 说明 | 用途 |
|------|------|------|
| `id` | NewsContent 的 MongoDB `_id` | 加购时作为 `cid` 参数 |
| `product_id` | 第一个 SKU 的 `productId`（MD5） | 加购时作为 `pid` 参数 |
| `title` | 商品标题 | 展示 |
| `sku` | 第一个真实 SKU 码 | 展示 |
| `unit_price` | 单价 | 展示 |

### 3.2 购物车 API（商城模块）

Base URL：`/shop/api/cart/`

详情请参阅商城模块文档，这里列出 AI 模块用到的接口：

#### 添加到购物车

```
POST /shop/api/cart/add
Content-Type: application/x-www-form-urlencoded

cid={content_id}&pid={product_id}&num={数量}

→ { "code": 0, "msg": "已加入购物车", "count": N }
```

#### 获取购物车列表

```
GET /shop/api/cart/items

→ {
    "code": 0,
    "data": {
        "items": [
            {
                "content_id": "...",
                "product_id": "...",
                "title": "...",
                "sku": "...",
                "qty": 10,
                "price": 20.0,
                "market_price": 25.0,
                "small_pic": "...",
                "url": "...",
                "price_source": "阶梯价 50-99 件档",
                "group_qty_prices": [...]
            }
        ],
        "count": 3
    }
}
```

#### 修改数量

```
POST /shop/api/cart/update
Content-Type: application/x-www-form-urlencoded

pid={product_id}&num={新数量}

→ { "code": 0, "msg": "ok" }
```

#### 删除商品

```
POST /shop/api/cart/remove
Content-Type: application/x-www-form-urlencoded

pid={product_id}

→ { "code": 0, "msg": "已删除" }
```

---

## 四、数据流

### 用户未登录（游客模式）

```
浏览器                        后端
  │                            │
  │  GET /shop/api/cart/items   │  首次访问，无 cart_token
  │◄──生成 UUID, set-cookie    │
  │                            │
  │  POST /shop/api/cart/add   │  加购
  │  Cookie: cart_token=UUID   │
  │◄──写入 ShoppingCartBll     │
  │    session_id=UUID         │
  │                            │
  │  POST /ai_cart/api/quote/chat  │  AI 对话
  │◄──搜索 NewsContent → 返回卡片 │
  │                            │
  │  点击 [+] → 调 cart/add    │  继续加购
```

### 用户登录

```
  │                            │
  │  POST /login               │  登录成功
  │◄──user_logged_in 信号      │
  │   ├─ 读取 cart_token cookie│
  │   ├─ 查找 session_id 匹配  │
  │   ├─ 合并到 user_id 名下   │
  │   └─ 清除 session_id       │
  │                            │
  │  GET /shop/api/cart/items  │  登录后购物车数据不变
```

---

## 五、品类处理器开发

AI 搜索核心逻辑通过品类处理器（Handler）实现，每个品类一个独立文件。

### 添加新品类

1. 在 `ai_handlers/` 下创建文件（如 `clothing.py`）
2. 定义 Processor 类，继承 `BaseHandler`
3. 在模块的 `__init__.py` 中 import（自动注册）

详见 `ai_handlers/` 目录下的示例文件。

---

## 六、常见问题

### Q: 切换品类后之前的提示词会被覆盖吗？

不会。`ensure_seeded()` 仅在数据库首次无配置时写入，切换品类后不会覆盖已有配置。如需重置可手动删除 `ShopQuotePrompts` 集合中的文档。

### Q: 为什么修改提示词后没有生效？

提示词配置无需重启。请刷新页面后重新发送消息。如果仍不生效，检查 `_get_prompt()` 的日志确认是否从 DB 读取到了值。

### Q: 商品搜不到怎么办？

1. 检查商品是否属于正确的 `class_id`（打印耗材：`6852498a0a8b42f2df14146e`）
2. 检查搜索关键词是否在 `column_3`~`column_10` 或 `title` 中
3. 查看后端日志中的 `[DEBUG 兜底搜索]` 确认是否进入兜底逻辑

### Q: 加入购物车后看不到商品？

1. 检查浏览器是否禁用了 Cookie（`cart_token` 依赖 Cookie）
2. 检查商城模块的"购物车必须登录才能访问"是否勾选
3. 检查后端日志 `[购物车合并]` 确认是否有异常

### Q: AI 返回 401 错误或原始 JSON 字符串怎么办？

401 错误：检查插件管理中的 API Key 是否有效，或切换到其他 AI 提供者。
原始 JSON 字符串：确认使用的是新插件系统的 AI 提供者（`plugins/ai_providers/`），而非旧的模块内 `ai_providers/`。