import csv
import json
import os
import re
from unittest import TestCase

from bson import ObjectId, json_util
from pymongo import MongoClient

import eb_utils
from eb_utils import http_utils
from eb_utils.email_utils import EmailUtils


class testCode(TestCase):


    def testSendEmeil(self):
        # 创建EmailSender实例（工作线程会自动启动）
        email_sender = EmailUtils("smtp.163.com", 465, "test@163.com", "111111", use_ssl=True)
        # 添加邮件到队列
        email_sender.add_to_queue("cqs263@gmail.com", "测试邮件", "测试邮件Test Body")

        # 等待所有邮件发送完成
        # email_sender.wait_for_completion()

        # 在程序结束时停止工作线程
        # email_sender.stop_workers()

    def testModelToDic(self):
        from entity.news_content_model import NewsContentModel
        model = NewsContentModel()
        dic_f = model.__dict__
        print(dic_f)

    def testOutputMongoDb(self):
        """
        项目发布前-导出安装默认需要的表及数据
        """
        # OutputDefaultData()

    def testImportFromCsv(self):
        mongo_client = MongoClient('mongodb://localhost:27017')
        # 选择或创建数据库
        mongo_db = mongo_client['xs_site']

        csv_file = "http://127.0.0.1:8019/db_bak/AdminMenus.json"
        # 获取 CSV 文件的表名（去除文件扩展名）
        collection_name = os.path.splitext(os.path.basename(csv_file))[0]
        collection = mongo_db[collection_name]
        # 清空集合
        # mongo_db[collection_name].delete_many({})
        file = http_utils.getText(csv_file)
        json_data = json.loads(file, object_hook=json_util.object_hook)
        # with open(csv_file, "r") as file:
        #     json_data = json.load(file, object_hook=json_util.object_hook)
        #collection.insert_many(json_data)

    def testPassWord(self):
        pass_word = eb_utils.random_string(8) # eb_utils.random_string(8)  # 随机生成8位密码
        print(pass_word)