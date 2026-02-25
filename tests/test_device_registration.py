import pytest
from httpx import AsyncClient
from fastapi import status
from skyproject.shared.api import app

@pytest.mark.asyncio
async def test_register_device():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/register-device", json={"user_id": "test_user", "token": "test_token", "platform": "ios"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Device registered successfully"}

@pytest.mark.asyncio
async def test_get_tokens():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/tokens")
    assert response.status_code == status.HTTP_200_OK
    assert "tokens" in response.json()
