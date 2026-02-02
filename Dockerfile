# FastReAct Docker Image
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    docker.io \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建工作区目录
RUN mkdir -p /root/.fastreact

# 暴露 Gateway 端口
EXPOSE 8765

# 默认命令
CMD ["python", "-m", "fastreact.cli.main", "chat"]
