
from typing import Tuple

from qcloud_cos import CosConfig, CosS3Client

from entity.file_model import FileModel
from plugins.plugin_base import Uploader, plugin_attribute


@plugin_attribute("文件上传-腾讯COS", "1.0", "ebsite")
class UploaderTencentCos(Uploader):

    def __init__(self, current_app):
        # self.name = "文件上传-腾讯COS"
        self.info = "将文件上传到腾讯COS对象存储"
        self.file_server: str = ""  # 自定义域名,访问文件时的域名https://file.ebsite.ai
        self.bucket: str = ""  # 存储桶名称,你在腾讯云COS创建的存储桶名称
        self.secret_id: str = ""  # 来自腾讯云COS的SecretId
        self.secret_key: str = ""  # 来自腾讯云COS的SecretKey
        self.region: str = "ap-beijing"  # ap-beijing
        super().__init__(current_app)



    def upload(self, fileb_bytes, model:FileModel) -> Tuple[bool, str]:
        # pip安装指南:pip install -U cos-python-sdk-v5

        # cos最新可用地域,参照https://www.qcloud.com/document/product/436/6224


        # 设置用户属性, 包括 secret_id, secret_key, region等。Appid 已在CosConfig中移除，请在参数 Bucket 中带上 Appid。Bucket 由 BucketName-Appid 组成
        secret_id = self.secret_id  # 替换为用户的 SecretId，请登录访问管理控制台进行查看和管理，https://console.cloud.tencent.com/cam/capi
        secret_key = self.secret_key  # 替换为用户的 SecretKey，请登录访问管理控制台进行查看和管理，https://console.cloud.tencent.com/cam/capi
        region = self.region  # 替换为用户的 region，已创建桶归属的region可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
        # COS支持的所有region列表参见https://www.qcloud.com/document/product/436/6224
        token = None  # 如果使用永久密钥不需要填入token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见https://cloud.tencent.com/document/product/436/14048
        domain = None # self.file_server  # domain可以不填，此时使用COS区域域名访问存储桶。domain也可以填写用户自定义域名，或者桶的全球加速域名
        # 填写用户自定义域名，比如user-define.example.com，需要先开启桶的自定义域名，具体请参见https://cloud.tencent.com/document/product/436/36638
        # 填写桶的全球加速域名，比如examplebucket-1250000000.cos.accelerate.tencentcos.cn，需要先开启桶的全球加速功能，请参见https://cloud.tencent.com/document/product/436/38864

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token,
                           Domain=domain)  # 获取配置对象
        client = CosS3Client(config)
        file_name = f"/upfile/{model._id}{model.type}"
        # 字节流 简单上传
        response = client.put_object(
            Bucket=self.bucket,
            Body=fileb_bytes,
            Key=file_name
        )
        print(response['ETag'])

        model.plugin_id = self.id
        model.plugin_name = self.name
        model.url = f"{self.file_server}{file_name}"


        return True, model.url

    def params_temp(self):
        """
        在后台保存插件配置时，实现在模板中添加保存参数
        :return: 模板字符串
        """
        return '''
                <div class="mb-3">
                    <label>SecretId</label> 
                    <div style="max-width:500px"  class="input-group">
                           <input placeholder="可以点击查看获取SecretId" name="secret_id" value="{{model.secret_id}}"  class="form-control" required>
                            <a target=_blank href="https://console.cloud.tencent.com/cam/capi" class="btn btn-primary">查看</a>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label>SecretKey</label>
                    <div style="max-width:500px"  class="input-group">
                           <input placeholder="可以点击查看获取SecretKey" name="secret_key" value="{{model.secret_key}}"  class="form-control" required>
                            <a target=_blank href="https://console.cloud.tencent.com/cam/capi" class="btn btn-primary">查看</a>
                    </div> 
                </div> 
                <div class="mb-3">
                    <label>存储桶名称</label>
                    <input name="bucket" placeholder="你在腾讯COS创建的存储桶名称"  value="{{model.bucket}}"  style="max-width:300px" class="form-control" required>
                </div> 
                <div class="mb-3">
                    <label>Region</label>
                    <div style="max-width:500px"  class="input-group">
                           <input placeholder="可以点击查看获取你的region" name="region" value="{{model.region}}"  class="form-control" required>
                            <a target=_blank href="https://console.cloud.tencent.com/cos5/bucket" class="btn btn-primary">查看</a>
                    </div>  
                </div> 
                <div class="mb-3">
                    <label>访问域名</label>
                    <input placeholder="文件的访问域名，可以在腾讯COS上自定义访问域名" name="file_server" value="{{model.file_server}}"  style="max-width:500px" class="form-control" required>
                </div>
                '''
