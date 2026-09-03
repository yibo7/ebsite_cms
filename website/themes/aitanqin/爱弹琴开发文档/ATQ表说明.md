# 一、GTP乐谱表
```
默认表eb_newscontent  
主要保存GTP文件的吉他乐谱
```
字段名称|说明
---|---
TitleStyle|作曲
SmallPic|封面图片，默认第一轨图片
Annex1|歌手
Annex2| 乐谱调性A到G（原歌手中文名称-如果是国外歌手）
Annex3|专辑名称
Annex4 | 难度级别(原歌曲中文名称-如果是英文歌曲)
Annex10 | 歌词
Annex5 | 文件上传的相对路径
Annex6 | 音轨名称，用{*}号分开（原midi路径）
Annex7 | 上传用户Id,用户逗号分开
Annex8 | 文件保存的绝对路径，临时保存用,不实际保存在数据库（不再使用）
Annex9 | 乐谱图片多个图片用英文逗号分开(原：音轨名称)
Annex16 | 售价
Annex11 | 音轨数
Annex12 | 小节数
Annex13 |  musicType:音乐类型，1总谱，2吉他独奏，3钢琴独奏，4架子鼓独奏，5贝斯独奏 6尤克里里独奏（ukulele）
Annex14 |  是否已经清理临时文件 0 否 1 是
Annex15 |  是否生成标签，由软件导入的乐谱需要标签未生成，然后在计划任务里定时更新
Annex21 | 文件生成图片状态，0等待审查，1审查通过（等待生成），2生成成功，1审查未通过（定期清理）， -2生成失败
Annex22 | 乐谱类型ID(对应类MusicTypeModel)
Annex23 | 乐谱国家编号，1中国,2欧美 3日本
Annex19 | 乐谱图片的数量
ContentInfo | 其他信息 
mdwu | 新字段-文件的md5值(只有唯一性)
oldmdwu | 新字段-旧的GTP文件MD5值，可以用来判断是否文件已经存在与将文件归类
Annex20| 是否使用文件服务，0不否，1为是，文件服务目前是f.aitanqin.com
# 二、MUSICXML乐谱表
```
表名称：xml_piano

主要为钢琴谱
内容模型：与 gtp差不多，不过换一个表，表名:eb_nc_xml_piano
```
字段名称|说明
---|---
TitleStyle | 副标题
SmallPic | 封面图片，默认第一轨图片
Annex1 | 歌手
Annex2 | 乐谱调性A到G（原歌手中文名称-如果是国外歌手）
Annex3 | 专辑名称
Annex4 | 难度级别(原歌曲中文名称-如果是英文歌曲)
Annex10 | 歌词
Annex5 | 文件上传的相对路径
Annex6 | 音轨名称，用{*}号分开（原midi路径）
Annex7 | 上传用户Id,用户逗号分开
Annex8 | 文件保存的绝对路径，临时保存用,不实际保存在数据库
Annex9 | 乐谱图片多个图片用英文逗号分开(原：音轨名称)
Annex11 | 音轨数
Annex12 | 小节数
Annex13 |  musicType:音乐类型，1总谱，2吉他独奏，3钢琴独奏，4架子鼓独奏，5贝斯独奏 6尤克里里独奏（ukulele）
Annex14 |  是否已经清理临时文件 0 否 1 是
Annex16 | 售价
Annex19 | 是否调用MuseDown生成图片 -1生成错误，0未生成，大于0生成成功，数字代表图片数量
Annex21 | 文件图片状态，0等待审查，1审查通过（等待生成），2生成成功（并审核通过），1审查未通过（定期清理）， -2生成失败
Annex23 | 乐谱国家编号，1中国,2欧美 3日本
ContentInfo | 其他信息
Annex20| 是否使用文件服务，0不否，1为是，文件服务目前是f.aitanqin.com
Annex19 | 乐谱图片的数量
# 三、AI图片乐谱表
```
AI图片脚本播放类表
eb_nc_imgtags
内容模型：
```
字段名称|说明
---|---
NewsTitle	|曲谱名称
Annex2   |  乐谱调性A到G（原歌手中文名称-如果是国外歌手）
Annex10	|	歌词
Annex5	|	媒体文件路径混合	支持mp3,mp4
Annex6	|	媒体文件路径（纯伴奏）
Annex1	|	歌手
Annex4	|	难度级别(原歌曲中文名称-如果是英文歌曲)
Annex13	|	音乐类型	musicType:音乐类型，1总谱，2吉他独奏，3钢琴独奏，4架子鼓独奏，5贝斯独奏 6尤克里里独奏（ukulele）
TitleStyle |	作曲		
Annex9		|乐谱图片多个图片用英文逗号分开
Annex8 |	播放脚本	,强制将此字段的类型修改为longtext,原为varchar 800 不够用	
ContentInfo	|	乐谱简介	
SmallPic |	封面图片(默认第一轨图片)
Annex14 | 是否已经清理临时文件 0 否 1 是
Annex16 |    售价
Annex21	|	文件生成图片状态，0等待审查,1审查通过(并审核通过)，-1审查未通过（定期清理）
Annex23 | 乐谱国家编号，1中国,2欧美 3日本
Annex24 | 是否添加水印 0否 1是
Annex25 | 是否制作播放脚本 0否 1是
Annex20| 是否使用文件服务，0不否，1为是，文件服务目前是f.aitanqin.com
Annex19 | 乐谱图片的数量

# 四、求谱表
```
表名称：qiupu
  
```
字段名称|说明
---|---
NewsTitle | 歌曲名称 
SmallPic | 封面小图片
Annex1 | 歌手
Annex2 | 歌手中文名称（如果是国外歌手）
Annex3 | 专辑名称
Annex4 | 歌曲中文名称（如果是英文歌曲）
Annex10 | 歌词  
Annex16 | 售价 
Annex21 | GTP文章生成状态，0未生成，1已生成
Annex23 | 乐谱国家编号，1中国,2欧美 3日本
ContentInfo | GTP文章
Annex9 | 封面图片大图 原:求谱人EMAIL或手机号,多个用#号分开
TitleStyle | 采集地址的MD5
Annex5 | 歌曲的站外播放页面
Annex8 | 求谱用户的ID，会去重，多个用逗号分开，字段被修改成longtext类型
Annex11| 简谱提交次数
Annex12 | 钢琴谱提交次数
Annex13 | 吉他谱提交次数
Annex22 | 简谱完成对应的内容ID
Annex24 | 钢琴谱完成对应的内容ID
Annex19 | 图片钢琴谱完成对应的内容ID
Annex25 | 数字吉他谱完成对应的内容ID
Annex20 | 图片吉他谱完成对应的内容ID