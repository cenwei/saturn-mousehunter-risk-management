"""
Saturn MouseHunter 风控管理 主程序入口
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Temporary imports - will be updated after shared lib is properly integrated
# from saturn_mousehunter_shared.foundation.logging import setup_logging
# from saturn_mousehunter_shared.infrastructure.settings import BaseSettings


from pydantic_settings import BaseSettings


class Risk-managementSettings(BaseSettings):
    service_name: str = "saturn-mousehunter-risk-management"
    port: int = 8084
    debug: bool = True
    log_level: str = "INFO"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    print(f"🚀 启动 Saturn MouseHunter 风控管理")
    yield
    print(f"🛑 关闭 Saturn MouseHunter 风控管理")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    settings = Risk-managementSettings()

    # setup_logging(
    #     service_name=settings.service_name,
    #     log_level=settings.log_level,
    # )

    app = FastAPI(
        title="Saturn MouseHunter 风控管理",
        description="Saturn MouseHunter 风控管理 API接口",
        version="0.1.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "risk-management"}

    # TODO: 添加业务路由

    return app


app = create_app()


def main():
    """主函数"""
    settings = Risk-managementSettings()
    uvicorn.run(
        "saturn_mousehunter_risk-management.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
