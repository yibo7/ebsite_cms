# 使用 Python 官方的 Docker 镜像作为基础镜像
FROM python:3.12.5

# 设置环境变量
ARG NAME

ENV NAME=${NAME}

# 设置工作目录
WORKDIR /app

# 复制应用代码到镜像中的 /app 目录
COPY ./ /app


# 安装应用依赖
# RUN pip install -r requirements.txt
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt


# 设置启动命令
# CMD python index.py
CMD ["uwsgi", "--ini", "uwsgi.ini"]