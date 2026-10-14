# CDN 静态文件
本系统将以下文件托管GitHub，并通过jsdelivrCDN访问
```html

<link rel="stylesheet" href="https://cdn.jsdelivr.com/gh/yibo7/ebcdn@1.0/bootstrap/4/css/bootstrap.min.css" type="text/css">
<script src="https://cdn.jsdelivr.com/gh/yibo7/ebcdn@1.0/jquery/jquery1.9.1.js"></script>
<script src="https://cdn.jsdelivr.net/gh/yibo7/ebcdn@1.0/bootstrap/4/js/bootstrap.min.js"></script>
```

但由于近期jsdelivr在中国无法访问，导致页面打开卡顿或打不开，可通过以下域名替换jsdelivr：
```
gcore.jsdelivr.net
fastly.jsdelivr.net
testingcf.jsdelivr.net
jsd.cdn.zzko.cn （由54ayao提供，稳如老狗，推荐）
jsdmirror.com
jsdmirror.cn
```
### 54ayao 介绍
> https://github.com/54ayao/JSDMirror