FROM python:3.12-slim

WORKDIR /app

# 安装uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src/ src/

# 安装依赖
RUN uv sync --frozen

# 暴露端口
EXPOSE 8084

# 启动命令
CMD ["uv", "run", "risk-management"]
