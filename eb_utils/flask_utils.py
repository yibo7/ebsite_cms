from flask import request, redirect, url_for

from eb_utils.eb_exceptions import EbTipError


def show_err(err):
    raise EbTipError(err)

def go_back():
    """
    如果有 referrer，则返回上一页；如果没有，则重定向到主页
    """
    return redirect(request.referrer or url_for('index'))

def get_client_ip():
    """
    获取客户端的 IP 地址，考虑了代理和负载均衡器的情况。
    """
    # 首先尝试从 X-Forwarded-For 头部获取 IP 地址
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # X-Forwarded-For 可能包含多个 IP 地址，我们取第一个
        ip = x_forwarded_for.split(',')[0]
    else:
        # 如果没有 X-Forwarded-For 头部，则使用 X-Real-IP
        x_real_ip = request.headers.get('X-Real-IP')
        if x_real_ip:
            ip = x_real_ip
        else:
            # 如果没有代理头部，则使用 Flask 的 request.remote_addr
            ip = request.remote_addr
    # 如果带端口就将端口去掉
    ip = ip.split(':')[0]
    return ip


