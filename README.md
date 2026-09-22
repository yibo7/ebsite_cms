# EbSite CMS — 开源 Flask 内容管理系统

<p align="center">
  <a href="https://eb.3k2k.com" target="_blank">🌐 前台演示</a>&nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="http://www.3k2k.com" target="_blank">🤖 AI 内容站演示</a>&nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyibo7%2Febsite_cms.git&env=SITE_KEY,MONGODB_SERV,MONGODB_NAME&project-name=ebsite_cms&repository-name=ebsite_cms" target="_blank">🚀 一键部署 Vercel</a>
</p>

---

## 目录

- [一、简介](#一简介)
- [二、核心功能](#二核心功能)
- [三、功能模块](#三功能模块)
- [四、技术栈与运行依赖](#四技术栈与运行依赖)
- [五、本地开发调试](#五本地开发调试)
- [六、部署方式](#六部署方式)
- [七、插件系统](#七插件系统)
- [八、多语言支持](#八多语言支持)
- [九、目录结构](#九目录结构)
- [十、使用声明](#十使用声明)

---

## 一、简介

**EbSite CMS** 是一款基于 **Python Flask 3.x** 的开源、轻量级、高扩展性的内容管理系统。适用于个人开发者、独立站长、中小型企业等场景。

### 核心优势

- **🆓 永久免费** — 开源免费，可自由使用与修改
- **⚡ 高性能** — 支持页面缓存、列表缓存、搜索缓存等多级缓存机制
- **🧩 模块化** — 模块系统 + 插件系统，功能可按需启用/停用
- **🛒 电商能力** — 内置商品管理、购物车、订单、支付（微信/支付宝）
- **🤖 AI 赋能** — 支持多供应商 AI 智能报价、AI 内容生成
- **🌐 多语言** — 内置国际化支持（中/英/日），自动浏览器语言检测
- **☁️ 多云部署** — 支持 Vercel、Docker、Windows 等多种部署方式
- **📱 API 开放** — 完整的 RESTful API，可对接小程序/APP

---

## 二、核心功能

### 用户与权限管理

| 功能 | 说明 |
|------|------|
| **前台用户系统** | 注册、登录、个人信息、收货地址、收藏、关注 |
| **后台管理员系统** | 多角色权限分配（RBAC），菜单权限颗粒度控制 |
| **验证码保护** | 图形验证码、登录频率限制（IP + 次数） |
| **第三方登录** | 支持微信扫码登录（插件化） |

### 内容管理

| 功能 | 说明 |
|------|------|
| **多级分类** | 无限级分类树，支持排序与移动 |
| **内容管理** | 文章/产品的增删改查，支持多字段自定义模型 |
| **专题聚合** | 创建专题将相关内容聚合展示，支持树形结构 |
| **标签系统** | 内容标签管理，支持按标签聚合与推荐 |
| **自定义表单** | 在线创建问卷、报名、反馈等表单，自动收集数据 |

### 模板与展示

| 功能 | 说明 |
|------|------|
| **模板引擎** | 基于 Jinja2，支持代码模板与文件模板两种模式 |
| **部件系统 (Widget)** | 可视化数据调用部件，可灵活插入页面任意位置 |
| **主题切换** | 多主题支持（aitanqin / eb_shop / eb_shop_quote / eblinks 等） |
| **列表缓存** | 内容列表自动缓存，减少数据库查询 |

### 扩展能力

| 功能 | 说明 |
|------|------|
| **模块系统** | 独立的功能模块，支持启用/停用/配置热更新 |
| **插件系统** | 短信、邮件、文件上传、支付、第三方登录等插件化 |
| **信号机制** | 基于 blinker 的事件监听（内容保存/支付成功/搜索预处理） |
| **内容模型** | 自定义字段类型，适应图文/文件/视频/商品等多类型数据 |

---

## 三、功能模块

EbSite CMS 采用模块化架构，每个模块独立注册，可在后台管理中启用/停用。

### 🛍️ 商城管理系统 (`eb_shop`)

基于内容模型的轻量电商解决方案：

- **商品管理** — 商品信息、多规格 SKU、货号唯一性校验
- **购物车** — 加入/删除/数量调整
- **订单管理** — 订单创建、状态跟踪
- **品牌专题** — 品牌分组展示
- **拆词搜索** — 支持多关键词 AND 匹配搜索商品与文章
- **支付集成** — 微信支付、支付宝

### 💰 积分管理系统 (`credits_sys`)

- 积分定价与购买
- 积分流水记录
- 积分申请与审核
- 支付回调处理

### 🤖 智能询价系统 (`eb_quote`)

AI 驱动的智能报价引擎：

- **多 AI 供应商** — 支持 DeepSeek、阿里千问 (Qwen)、京东 JoyAgent
- **品类处理器** — 插件式品类架构，当前支持：硒鼓/墨粉 (`printer_drum`)、服装 (`clothing`)
- **智能对话** — 客户通过对话描述需求，AI 自动匹配商品并生成报价单
- **提示词配置** — 后台可编辑系统提示词、欢迎语等，无需重启
- **报价记录** — 完整的报价历史与详情

### 🎵 爱弹琴 (`aitanqin` / AI_TAN_QIN)

乐谱管理与 APlayer 服务：

- **乐谱管理** — 乐谱文件上传与分发
- **API 服务** — 乐谱文件获取接口（带频率限制）
- **APlayer 播放器** — 完整的 SPA 音乐播放器前端

### 📡 AI 内容管理

通过 GitHub Actions 定时触发，AI 自动更新网站内容：

- 定时任务（每日北京时间 08:00 触发）
- 支持手动触发（`workflow_dispatch`）
- 调用 `/api/ai_update` 接口实现内容自动生成

---

## 四、技术栈与运行依赖

### 运行环境

| 组件 | 版本/类型 | 说明 |
|------|----------|------|
| **Python** | ≥ 3.12 | 运行语言 |
| **Flask** | 3.0.x | Web 框架 |
| **MongoDB** | ≥ 5.0 | 主数据库（推荐 [MongoDB Atlas](https://cloud.mongodb.com) 免费 512MB） |
| **Redis** | 可选 | 缓存加速（推荐 [Redis Cloud](https://app.redislabs.com) 免费 30MB） |

### 核心依赖

```
Flask==3.0.3         # Web 框架
pymongo==4.6.3       # MongoDB 驱动
redis==4.6.0         # Redis 驱动
Pillow==10.3.0       # 图片处理
gevent==24.2.1       # WSGI 服务器
flask-cors==5.0.0    # 跨域支持
flask_caching        # 缓存抽象层
blinker==1.8.2       # 信号机制
xmltodict==0.13.0    # XML 解析
cos-python-sdk-v5    # 腾讯云 COS（可选）
python-dotenv        # 环境变量（仅本地开发）
```

---

## 五、本地开发调试

### 1. 克隆项目

```bash
git clone https://github.com/yibo7/ebsite_cms.git
cd ebsite_cms
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

编辑 `conf/setting.json`：

```json
{
    "MONGODB_SERV": "mongodb://user:password@host:port/?authSource=admin",
    "MONGODB_NAME": "eb_shop",
    "APP_KEY": "your-app-key",
    "ThemeName": "eb_shop_quote",
    "IsDebug": true,
    "Port": 8066,
    "DefaultLang": "auto"
}
```

> 也可通过环境变量 `MONGODB_SERV`、`MONGODB_NAME`、`APP_KEY` 覆盖配置。

### 4. 启动

```bash
python index.py
```

访问 `http://localhost:8066` 查看前台。

### 5. 后台初始化

首次启动后访问 `http://localhost:8066/admin/login_ad`，根据提示完成数据初始化，即可进入后台管理。

---

## 六、部署方式

### ☁️ Vercel 部署（推荐）

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyibo7%2Febsite_cms.git&env=SITE_KEY,MONGODB_SERV,MONGODB_NAME&project-name=ebsite_cms&repository-name=ebsite_cms)

一键部署，需配置以下环境变量：

| 变量名 | 说明 |
|--------|------|
| `MONGODB_SERV` | MongoDB 连接字符串 |
| `MONGODB_NAME` | 数据库名称 |
| `APP_KEY` (或 `SITE_KEY`) | 站点密钥 |

> Vercel 环境自动使用 `MongoCache`（基于 MongoDB 的缓存）替代 Redis。

详细教程：[在 Vercel 上运行](doc/项目部署/1.在Vercel上运行.md)

### 🐳 Docker 部署

```bash
docker-compose up -d
```

> 默认使用 1Panel 网络，可根据实际环境修改 `docker-compose.yml`。

详细教程：[在 Docker 上运行](doc/项目部署/2.在Docker上运行.md)

### 🪟 Windows 部署

```bash
python index.py
```

或使用 uWSGI：

```bash
uwsgi --ini uwsgi.ini
```

详细教程：[在 Windows 上运行](doc/项目部署/3.在windows上运行.md)

---

## 七、插件系统

EbSite CMS 提供丰富的插件体系，所有插件可在后台管理中配置。

### 插件类型

| 类型 | 已实现 | 说明 |
|------|--------|------|
| **短信发送** | ✅ 腾讯云 SMS | 发送短信验证码/通知 |
| **邮件发送** | ✅ 默认 SMTP | 发送邮件通知/测试 |
| **文件上传** | ✅ 本地 / MongoDB / 腾讯云 COS | 灵活的文件存储后端 |
| **第三方登录** | ✅ 微信登录 | 扫码登录 |
| **在线支付** | ✅ 微信支付 / 支付宝 | 支付集成 |

### 扩展开发

所有插件继承自 `PluginBase`，只需实现对应的抽象方法即可开发新插件：

```python
@plugin_attribute('插件名称', '1.0', '作者')
class MyPlugin(PluginBase):
    def __init__(self, app):
        super().__init__(app)
        # 初始化逻辑
```

---

## 八、多语言支持

EbSite CMS 内置国际化引擎，支持按 URL 前缀或浏览器语言自动切换。

### 已支持语言

| 语言 | 代码 | 状态 |
|------|------|------|
| 简体中文 | `zh` | ✅ |
| English | `en` | ✅ |
| 日本語 | `ja` | ✅ |

### 语言检测优先级

1. **URL 前缀** — `/en/page` 强制使用英文
2. **浏览器语言** — 当 `DefaultLang=auto` 时，自动检测浏览器 `Accept-Language`
3. **站点默认语言** — 上述均未匹配时使用配置的默认语言

### 语言文件

位于 `website/themes/<主题名>/i18n/` 目录下，以 JSON 格式存放翻译键值对。

---

## 九、目录结构

```
ebsite_cms/
├── index.py                    # 应用入口
├── conf/
│   └── setting.json            # 基础配置（MongoDB、主题等）
├── website/
│   ├── __init__.py             # Flask 应用工厂
│   ├── pages/                  # 前台页面（CMS 路由、支付等）
│   ├── pages_admin/            # 后台管理页面
│   ├── pages_ucc/              # 用户中心
│   ├── apis/                   # RESTful API
│   └── themes/                 # 主题系统
│       ├── aitanqin/           #   ├── 爱弹琴主题（含 i18n）
│       ├── default/            #   ├── 默认后台主题
│       ├── eb_shop/            #   ├── 商城主题
│       ├── eb_shop_quote/      #   ├── 智能报价主题
│       └── eblinks/            #   └── 链接主题
├── eb_modules/                 # 功能模块
│   ├── credits_sys/            #   ├── 积分系统
│   ├── eb_shop/                #   ├── 商城系统
│   ├── eb_quote/               #   ├── 智能报价系统
│   │   ├── ai_providers/       #   │   ├── AI 供应商（DeepSeek/Qwen/JoyAgent）
│   │   ├── ai_handlers/        #   │   └── 品类处理器（硒鼓/服装）
│   │   └── datas/              #   │   └── 数据层（报价记录、提示词配置）
│   ├── aitanqin/               #   ├── AI 乐谱服务
│   └── app_apis/               #   └── 小程序/APP 开放接口
├── plugins/                    # 插件系统
│   ├── payments/               #   ├── 支付插件（微信/支付宝）
│   ├── email_sender_default.py #   ├── 邮件发送
│   ├── sms_sender_tencent.py   #   ├── 腾讯云短信
│   ├── uploader_*.py           #   ├── 文件上传（本地/MongoDB/COS）
│   └── open_login_weixin.py    #   └── 微信登录
├── bll/                        # 业务逻辑层
├── entity/                     # 数据模型实体
├── eb_utils/                   # 工具库
├── eb_cache/                   # 缓存层（SimpleCache / Redis / MongoCache）
├── db_utils/                   # 数据库初始化
├── decorators.py               # 装饰器（权限/限流/SiteKey 验证）
├── signals.py                  # 信号定义（blinker）
├── docker-compose.yml          # Docker Compose 配置
├── Dockerfile                  # Docker 镜像构建
├── uwsgi.ini                   # uWSGI 配置
└── requirements.txt            # Python 依赖
```

---

## 十、使用声明

EbSite CMS 及各系列产品免费开源，你可以自行使用与修改。但在使用 EbSite 产品开发项目时请遵守以下规定：

1. **请保留代码官方出处声明**
2. **不得使用 EbSite 开发违法违规项目**
3. **不得使用 EbSite 开发违背道德伦理的项目**

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/yibo7">yibo7</a>
  <br>
  <a href="https://eb.3k2k.com">🌐 演示站点</a>&nbsp;·&nbsp;
  <a href="https://github.com/yibo7/ebsite_cms">📦 GitHub</a>
</p>