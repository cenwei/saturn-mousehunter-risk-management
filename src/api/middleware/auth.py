"""
JWT Authentication Middleware
JWT认证中间件 - 调用认证微服务验证token
"""
import httpx
from typing import Optional
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from saturn_mousehunter_shared.log.logger import get_logger
from infrastructure.config.app_config import get_app_config

log = get_logger(__name__)
security = HTTPBearer()
config = get_app_config()


class AuthService:
    """认证服务客户端"""

    def __init__(self, auth_service_url: str):
        self.auth_service_url = auth_service_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)

    async def verify_token(self, token: str) -> Optional[dict]:
        """
        调用认证微服务验证token
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.client.get(
                f"{self.auth_service_url}/api/v1/users/me",
                headers=headers
            )

            if response.status_code == 200:
                user_data = response.json()
                log.info(f"Token verification successful for user: {user_data.get('username')}")
                return user_data
            else:
                log.warning(f"Token verification failed: {response.status_code}")
                return None

        except Exception as e:
            log.error(f"Error verifying token with auth service: {e}")
            return None

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局认证服务实例
auth_service = AuthService(config.auth_service_url)


async def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> dict:
    """
    获取当前用户信息
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = await auth_service.verify_token(credentials.credentials)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_data


async def get_current_active_user(current_user: dict = get_current_user) -> dict:
    """
    获取当前活跃用户
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def require_admin(current_user: dict = get_current_active_user) -> dict:
    """
    要求管理员权限
    """
    if current_user.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def require_risk_manager(current_user: dict = get_current_active_user) -> dict:
    """
    要求风控管理员权限
    """
    user_type = current_user.get("user_type")
    if user_type not in ["admin", "risk_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Risk manager privileges required"
        )
    return current_user