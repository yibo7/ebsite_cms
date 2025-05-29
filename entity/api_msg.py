class ApiMsg:
    def __init__(self, data=None):
        self.data = data
        self.msg = ''
        self.code = 0


def api_err_permission(err: str = "No permission"):
    api_msg = ApiMsg()
    api_msg.msg = err
    api_msg.code = 401
    # api_msg.success = False
    return api_msg.__dict__


def api_err(err: str = "No permission", code=-1):
    api_msg = ApiMsg()
    api_msg.msg = err
    api_msg.code = -1
    # api_msg.success = False
    return api_msg.__dict__


def api_succesful(data, info: str = "succesful"):
    api_msg = ApiMsg(data)
    api_msg.msg = info
    api_msg.code = 0
    # api_msg.success = True
    return api_msg.__dict__
