
# 一、关于 EbSite CMS

你可以一键将EbSite CMS，可以部署在python环境下，也可以部署在vercel平台上，只需一个申请免费的MongoDb，
即可永久拥有免费而强大的独立网站。

### 主要功能项：
- 前后台用户及权限管理
- 分类、内容与专题管理
- 可扩展CMS内容模型
- 可扩展数据调用部件
- 自定义表单系统
- 可定制主题皮肤
- 可监听触发器（事件）
- 插件管理系统
- 部件管理系统
- 模块管理系统
- 积分系统
- 支付系统（支持微信支付）
- 提供完整的APP接口（可用来快速对接小程序与APP）
 

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

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyibo7%2Febsite_cms.git&env=SITE_KEY,MONGODB_SERV,MONGODB_NAME&envDescription=SITE_KEY%20is%20the%20site%20secret%2C%20MONGODB_SERV%20is%20the%20MongoDB%20connection%20string%2C%20MONGODB_NAME%20is%20the%20database%20name%20(optional%2C%20uses%20default%20if%20empty)&project-name=ebsite_cms&repository-name=ebsite_cms)


> 更多请参考教程[《项目部署教程》](doc/项目部署.md)

# 五、使用声明
EbSite及系列产品免费开源，你可以自行使用与修改，但你在使用EbSite产品开发项目的同时要遵守以下规定:
- 1、请保留代码官方出处声明
- 2、不得使用EbSite开发违法违规项目
- 3、不得使用EbSite开发违背道德伦理的项目


