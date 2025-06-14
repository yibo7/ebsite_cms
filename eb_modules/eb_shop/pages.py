import time

from flask import jsonify, current_app, render_template, redirect, request

from decorators import check_admin_login
from eb_modules.eb_shop import bp_shop_pages
from entity.user_token import UserToken

# region 管理后台页面
@bp_shop_pages.route('/shop_orders', methods=['GET'])
@check_admin_login
def shop_orders(admin_token:UserToken):

    return render_template("shop_admin/shop_orders.html")

# endregion
