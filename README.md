# saturn-mousehunter-risk-management

Saturn MouseHunter 风控管理

## 快速开始

### 开发环境

1. 安装依赖:
```bash
uv sync
```

2. 启动数据库:
```bash
cd docker/dev
docker-compose up -d db redis
```

3. 运行数据库迁移:
```bash
uv run alembic upgrade head
```

4. 启动服务:
```bash
uv run risk-management
```

### Docker开发

```bash
cd docker/dev
docker-compose up
```

## API文档

服务启动后访问:
- Swagger UI: http://localhost:8084/api/v1/docs
- ReDoc: http://localhost:8084/api/v1/redoc

## 测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html
```

## 开发规范

- 使用 `ruff` 进行代码格式化
- 使用 `mypy` 进行类型检查
- 遵循 Clean Architecture 设计原则
