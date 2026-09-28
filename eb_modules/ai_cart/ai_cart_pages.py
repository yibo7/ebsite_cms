from flask import redirect, render_template, request

from decorators import check_admin_login
from . import bp_ai_cart_pages
from entity.user_token import UserToken


@bp_ai_cart_pages.route('/', methods=['GET', 'POST'])
def credits_index():
    return redirect('chat/index.html')


# region 管理后台页面

@bp_ai_cart_pages.route('/shop_quote_prompts', methods=['GET', 'POST'])
@check_admin_login
def shop_quote_prompts(admin_token: UserToken):
    """AI 提示词配置（后台）"""
    from .datas.prompts_config import ShopQuotePrompts

    bll = ShopQuotePrompts()
    config = bll.get_config()

    if request.method == 'POST':
        data = {
            "shop_name": request.form.get("shop_name", "").strip(),
            "welcome_message": request.form.get("welcome_message", "").strip(),
            "extract_prompt": request.form.get("extract_prompt", "").strip(),
            "sales_prompt_tpl": request.form.get("sales_prompt_tpl", "").strip(),
            "guide_prompt": request.form.get("guide_prompt", "").strip(),
        }
        bll.save_config(data)

        return redirect(bp_ai_cart_pages.url_prefix + '/shop_quote_prompts?saved=1')

    saved = bool(request.args.get("saved", False))

    # 从当前 Handler 加载品类默认值作为展示提示
    from .ai_handlers import get_ai_handler
    handler = get_ai_handler()

    return render_template(
        "shop_admin/prompts_config.html",
        config=config, saved=saved,
        defaults={
            "shop_name": getattr(handler, "default_shop_name", ""),
            "welcome_message": getattr(handler, "default_welcome_message", ""),
            "extract_prompt": getattr(handler, "default_extract_prompt", ""),
            "sales_prompt_tpl": getattr(handler, "default_sales_prompt_tpl", ""),
            "guide_prompt": getattr(handler, "default_guide_prompt", ""),
        }
    )
# endregion
