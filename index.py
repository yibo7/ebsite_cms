from flask import request, render_template
from flask_cors import CORS
from gevent.pywsgi import WSGIServer

from decorators import check_session
from eb_utils.eb_exceptions import EbTipError
from website import create_app

app = create_app()
app.config['cdn'] = 'https://cdn.jsdmirror.com' # https://gcore.jsdelivr.net' # https://cdn.jsdelivr.net'

@app.before_request
def after_request():
    request.session_id = request.cookies.get('session_id')


@app.after_request
@check_session
def after_request(response):
    return response


# 定义404错误页面
@app.errorhandler(404)
def not_found_error(error):

    return render_template('404.html', code=404,errinfo="抱歉，找不到当前页面！"), 404


@app.errorhandler(Exception)
def handle_exception(error):
    # app.logger.error(error)  # 打印错误日志
    # 记录完整的异常信息，包括堆栈跟踪

    app.logger.exception("发生未捕获的异常: %s", error)

    return render_template('err.html',code=500, errinfo=error), 500


@app.errorhandler(EbTipError)
def handle_exception(error):

    return render_template('err.html',code=10001, errinfo=error), 500

if __name__ == '__main__': # 以下在使用 uWSGI 时不会被执行，但对本地开发有用

    port = app.config['base_settings']['Port']
    is_debug = app.config['base_settings']['IsDebug']
    if is_debug:
        CORS(app)  # 同源策略可以通过，从而允许跨域请求，只是为了方便客户端调式使用，上线后会去掉
        print("dev site starting...")
        app.run(host='0.0.0.0', port=port, debug=False)

    else:
        http_server = WSGIServer(("0.0.0.0", port), app)
        print("pro site starting...")
        http_server.serve_forever()

