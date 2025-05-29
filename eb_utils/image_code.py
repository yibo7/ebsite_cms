import base64
import random
import string
from io import BytesIO

from PIL import Image, ImageFont, ImageDraw
from flask import make_response

import eb_cache
import eb_utils
from db_utils import redis_utils
from eb_cache import login_utils


class ImageCode:
    """
    验证码处理
    """

    def rndColor(self):
        """随机颜色"""
        return (random.randint(32, 127), random.randint(32, 127), random.randint(32, 127))

    def geneText(self):
        """生成4位验证码"""
        return ''.join(random.sample(string.ascii_letters + string.digits, 4))  # ascii_letters是生成所有字母 digits是生成所有数字0-9

    def drawLines(self, draw, num, width, height):
        """划线"""
        for num in range(num):
            x1 = random.randint(0, int(width / 2))
            y1 = random.randint(0, int(height / 2))
            x2 = random.randint(0, width)
            y2 = random.randint(int(height / 2), height)
            draw.line(((x1, y1), (x2, y2)), fill='black', width=1)

    def getVerifyCode(self):
        """生成验证码图形"""
        code = self.geneText()
        # 图片大小120×50
        width, height = 100, 30
        # 新图片对象
        im = Image.new('RGB', (width, height), 'white')
        # 字体
        font = ImageFont.truetype('website/themes/kawoszeh.ttf', 20)
        # 加载默认字体并设置文字大小
        # font = ImageFont.load_default()
        # draw对象
        draw = ImageDraw.Draw(im)
        # 绘制字符串
        for item in range(4):
            draw.text((5 + random.randint(-3, 3) + 23 * item, 5 + random.randint(-3, 3)),
                      text=code[item], fill=self.rndColor(), font=font)
        # 划线
        self.drawLines(draw, 2, width, height)
        return im, code

    def getImgCode(self):
        image, code = self.getVerifyCode()
        # 图片以二进制形式写入
        buf = BytesIO()
        image.save(buf, 'jpeg')
        buf_str = buf.getvalue()
        # 把buf_str作为response返回前端，并设置首部字段
        response = make_response(buf_str)
        response.headers['Content-Type'] = 'image/gif'
        # 将验证码字符串储存在session中
        # session[SessionIds.ImageCode] = code
        cache_key = login_utils.get_safe_coe_key()
        if cache_key:
            eb_cache.set_ex_minutes(code, 10, cache_key)
        return response

    def check_code(self,image_code:str):
        safe_key = login_utils.get_safe_coe_key()
        if not (safe_key and image_code and eb_cache.exists_key(safe_key)):
            return False, '验证码无效'

        safe_code = eb_cache.get(safe_key).lower()
        if not safe_code:
            return False, '验证码无效或过期'

        if safe_code != image_code.lower():
            return False, '验证码不正确'
        eb_cache.delete(safe_key)
        return True, ''

    def getAppImgCode(self):
        image, code = self.getVerifyCode()
        # 图片以二进制形式写入
        buf = BytesIO()
        image.save(buf, 'jpeg')
        image_bytes  = buf.getvalue()
        # 将bytes转换为base64编码
        base64_code = base64.b64encode(image_bytes)
        base64_code_str = base64_code.decode('utf-8')  # 将bytes转换为字符串
        cache_key = f'safe_{eb_utils.get_uuid()}'
        print(f'图片验证码：{code}')
        eb_cache.set_ex_minutes(code, 10, cache_key)
        return cache_key,base64_code_str

    def check_app_code(self,code_key: str,image_code:str):

        if not all([code_key, image_code]):
            return '请传入code_key与code'
        safe_code = eb_cache.get(code_key)
        if not safe_code:
            return '验证码无效或过期'

        if safe_code.lower() != image_code.lower():
            return '验证码不正确'
        eb_cache.delete(code_key)
        return ''