"""
主程序测试
"""
import pytest
from fastapi.testclient import TestClient
from saturn_mousehunter_risk-management.main import app

client = TestClient(app)


def test_health_check():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "risk-management"
