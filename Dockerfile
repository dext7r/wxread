# 多阶段构建优化的Dockerfile
FROM python:3.11-slim as builder

# 设置构建参数
ARG BUILD_DATE
ARG VERSION=2.0.0

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential &&
  rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --user -r requirements.txt

# 生产阶段
FROM python:3.11-slim

# 设置标签
LABEL maintainer="wxread-team" \
  version="${VERSION}" \
  description="微信读书自动阅读工具" \
  build-date="${BUILD_DATE}"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  TZ=Asia/Shanghai \
  PATH="/home/wxread/.local/bin:${PATH}"

# 创建非root用户
RUN groupadd -r wxread && useradd -r -g wxread -d /home/wxread -s /bin/bash wxread

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
  cron \
  curl &&
  rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python包
COPY --from=builder /root/.local /home/wxread/.local

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY --chown=wxread:wxread . .

# 创建日志目录
RUN mkdir -p /app/logs && chown -R wxread:wxread /app/logs

# 创建cron任务
RUN echo "0 1 * * * cd /app && /usr/local/bin/python3 main.py >> /app/logs/\$(date +\%Y-\%m-\%d).log 2>&1" >/etc/cron.d/wxread-cron &&
  chmod 0644 /etc/cron.d/wxread-cron &&
  crontab /etc/cron.d/wxread-cron

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import sys; sys.path.insert(0, 'src'); from src.utils.logger import get_logger; print('OK')" || exit 1

# 切换到非root用户
USER wxread

# 暴露端口（如果需要）
# EXPOSE 8080

# 启动命令
CMD ["sh", "-c", "cron && tail -f /dev/null"]
