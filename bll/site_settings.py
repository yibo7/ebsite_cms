from bson import ObjectId
from pymongo.database import Database


class SiteSettings:
    def __init__(self, db: Database):
        self.table = db['SiteSettings']
        self.key_name = 'site_setting_key'

    def default_model(self) -> dict:
        model = {
            "_id": self.key_name,
            "err_login_lock": "3",
            "is_open_safe_code": True,
            "reg_group_id": "66b4926df455dd91ca3de33e",
            "site_name": "ebsite",
            "sms_sender_id": "TencentSMSSender",
            "email_sender_id": "DefaultEmailSender",
            "report_emails": "ebsite@gmail.com",
            "uploader_id": "UploaderMongoDb",
            "upload_max_size": "1",
            "upload_types": ".gif, .png, .jpg, .jpeg, .bmp, .rar, .zip, .txt, .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .csv, .mp3, .mp4, .avi, .mov, .wmv",
            "app_token_expired": "24"
        }
        return model


    def save_setting(self,model:dict):
        model['_id'] = self.key_name
        self.table.update_one({"_id": self.key_name}, {"$set": model}, upsert=True) # 如果没有就添加


    def get_settings(self) -> dict:
        return self.table.find_one({"_id": self.key_name}) or self.default_model()