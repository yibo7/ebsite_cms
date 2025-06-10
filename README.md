
# 一、关于 EbSite CMS

## EbSite CMS 简介

**EbSite CMS** 是一款开源、轻量级、高扩展性的内容管理系统，适用于个人开发者、独立站长、中小型企业等多种应用场景。

你可以 **一键部署 EbSite CMS**，支持运行在本地 Python 环境，也可以直接部署在 **Vercel 平台** 上。只需申请一个免费的 **MongoDB 数据库（MongoDB Atlas）**，即可永久免费拥有一个功能强大、完全独立、可定制化的内容网站。

--- 
🔗 **演示地址（Demo）**：

👉 [https://eb.3k2k.com](https://eb.3k2k.com)（前台）

👉 [后台图示](doc/admin.png) （不一定是最新版）
 

## 核心功能特色

* ✅ **前后台用户及权限管理**
  支持多角色权限分配，前台/后台账户系统分离，确保站点安全与管理灵活性。

* ✅ **分类、内容与专题管理**
  结构化管理内容，支持多级分类、标签、专题聚合，适应多样化的内容组织需求。

* ✅ **可扩展 CMS 内容模型**
  自定义内容模型字段，支持图文、文件、视频等多类型数据。

* ✅ **可扩展数据调用部件（Widget）**
  支持创建自定义数据展示部件，可灵活用于前台页面内容渲染。

* ✅ **自定义表单系统**
  快速创建在线问卷、报名、反馈等表单，收集用户提交数据。

* ✅ **主题皮肤系统（支持定制）**
  使用模板引擎，支持完全自定义前端样式或快速切换主题。

* ✅ **事件监听与触发器系统**
  支持基于事件的自动处理机制，便于与外部服务或插件集成。

* ✅ **插件系统**
  可通过插件拓展系统功能，支持插件启用/禁用/配置等操作。

* ✅ **部件（Widget）管理系统**
  支持在页面布局中插入各类可视化内容块，提升页面表现力。

* ✅ **模块管理系统**
  模块化开发与部署，适配不同业务需求与系统构建。

* ✅ **积分系统**
  支持用户行为积分奖励，可用于论坛、内容互动、商城等场景。

* ✅ **支付系统（支持微信支付）**
  内置支付集成，支持微信支付，适用于会员系统、内容付费、商品购买等业务。

* ✅ **APP/小程序开放接口**
  提供完整的 RESTful API，可用于快速构建微信小程序、APP 等移动端产品。

* ⬜ **AI内容管理模块(测试中)**
  你只需要一个想法，让AI帮你网站分类的建设，并按照你的计划自动更新网站文章，当然你也可自定义分类，自定义创作内容的关键词。
  （演示：https://www.3k2k.com）
# 二、运行依赖 
- 运行环境：Python 3.12， Flask 3.x 部署。
- 数据库: MongoDb
    - 免费申请512MB: https://cloud.mongodb.com
- 缓存(可选): Redis
    - 免费申请30M: https://app.redislabs.com
 
 
# 三、本地调试
将项目clone到本地后，可用pytharm（vs code）打开。
安装依赖：
> pip install -r requirements.txt

运行：
> python index.py

# 四、部署

立即创建我的网站：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyibo7%2Febsite_cms.git&env=SITE_KEY,MONGODB_SERV,MONGODB_NAME&project-name=ebsite_cms&repository-name=ebsite_cms)

详细部署教程：
- [在Vercel上运行](doc/项目部署/1.在Vercel上运行.md)
- [在Docker上运行](doc/项目部署/2.在Docker上运行.md)
- [在windows上运行](doc/项目部署/3.在windows上运行.md)

# 五、使用声明
EbSite及系列产品免费开源，你可以自行使用与修改，但你在使用EbSite产品开发项目的同时要遵守以下规定:
- 1、请保留代码官方出处声明
- 2、不得使用EbSite开发违法违规项目
- 3、不得使用EbSite开发违背道德伦理的项目


