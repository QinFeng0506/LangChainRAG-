"""认证模块测试 —— 注册、登录、Token 刷新、密码修改、权限校验。"""
import pytest


class TestRegister:
    """用户注册测试。"""

    async def test_register_success(self, client):
        """正常注册应返回 Token 和用户信息。"""
        resp = await client.post("/api/auth/register", json={
            "username": "newuser", "password": "pass123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["username"] == "newuser"
        assert data["role"] == "user"

    async def test_register_duplicate_username(self, client):
        """重复用户名应返回 409 冲突。"""
        await client.post("/api/auth/register", json={"username": "dup", "password": "pass123"})
        resp = await client.post("/api/auth/register", json={"username": "dup", "password": "pass123"})
        assert resp.status_code == 409
        assert "已存在" in resp.json()["detail"]

    async def test_register_short_username(self, client):
        """用户名少于 3 字符应返回 422 校验错误。"""
        resp = await client.post("/api/auth/register", json={"username": "ab", "password": "pass123"})
        assert resp.status_code == 422

    async def test_register_short_password(self, client):
        """密码少于 6 字符应返回 422 校验错误。"""
        resp = await client.post("/api/auth/register", json={"username": "testuser", "password": "12345"})
        assert resp.status_code == 422

    async def test_register_empty_username(self, client):
        """空用户名应返回 422。"""
        resp = await client.post("/api/auth/register", json={"username": "", "password": "pass123"})
        assert resp.status_code == 422


class TestLogin:
    """登录测试。"""

    async def test_login_success(self, client, admin_token):
        """管理员登录应成功返回 Token。"""
        resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"
        assert len(data["access_token"]) > 50

    async def test_login_wrong_password(self, client):
        """错误密码应返回 401。"""
        resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "wrongpass"
        })
        assert resp.status_code == 401
        assert "错误" in resp.json()["detail"]

    async def test_login_nonexistent_user(self, client):
        """不存在的用户名应返回 401。"""
        resp = await client.post("/api/auth/login", json={
            "username": "nobody", "password": "pass123"
        })
        assert resp.status_code == 401

    async def test_login_empty_fields(self, client):
        """空字段应返回验证错误或认证失败。"""
        resp = await client.post("/api/auth/login", json={"username": "", "password": ""})
        assert resp.status_code in (401, 422)


class TestTokenRefresh:
    """Token 刷新测试。"""

    async def test_refresh_success(self, client):
        """有效 refresh_token 应返回新 Token。"""
        reg = await client.post("/api/auth/register", json={"username": "rftest", "password": "pass123"})
        refresh = reg.json()["refresh_token"]

        resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "rftest"
        # 新 access_token 应有效且包含 access 类型
        assert len(data["access_token"]) > 50

    async def test_refresh_invalid_token(self, client):
        """无效 refresh_token 应返回 401。"""
        resp = await client.post("/api/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert resp.status_code == 401

    async def test_refresh_access_token_as_refresh(self, client):
        """用 access_token 作为 refresh_token 应被拒绝。"""
        reg = await client.post("/api/auth/register", json={"username": "atest", "password": "pass123"})
        access = reg.json()["access_token"]

        resp = await client.post("/api/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401


class TestGetMe:
    """当前用户信息查询测试。"""

    async def test_get_me_authenticated(self, client, auth_headers):
        """已登录用户应返回用户信息。"""
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    async def test_get_me_no_token(self, client):
        """无 Token 请求应返回 401。"""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client):
        """伪造 Token 应返回 401。"""
        resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer fake.token.here"})
        assert resp.status_code == 401


class TestChangePassword:
    """密码修改测试。"""

    async def test_change_password_success(self, client, user_headers):
        """提供正确旧密码应成功修改。"""
        resp = await client.put("/api/user/password", headers=user_headers, json={
            "old_password": "test123", "new_password": "newpass456"
        })
        assert resp.status_code == 200
        assert "成功" in resp.json()["message"]

        # 用新密码应能登录
        login_resp = await client.post("/api/auth/login", json={
            "username": "testuser", "password": "newpass456"
        })
        assert login_resp.status_code == 200

    async def test_change_password_wrong_old(self, client, user_headers):
        """旧密码错误应返回 400。"""
        resp = await client.put("/api/user/password", headers=user_headers, json={
            "old_password": "wrongpass", "new_password": "newpass456"
        })
        assert resp.status_code == 400

    async def test_change_password_short_new(self, client, user_headers):
        """新密码太短应返回 422。"""
        resp = await client.put("/api/user/password", headers=user_headers, json={
            "old_password": "test123", "new_password": "12345"
        })
        assert resp.status_code == 422

    async def test_change_password_no_auth(self, client):
        """未登录修改密码应返回 401。"""
        resp = await client.put("/api/user/password", json={
            "old_password": "old", "new_password": "newpass"
        })
        assert resp.status_code == 401


class TestPermissions:
    """权限控制测试。"""

    async def test_admin_can_access_knowledge(self, client, auth_headers):
        """管理员应能访问知识库管理。"""
        resp = await client.get("/api/knowledge/stats", headers=auth_headers)
        assert resp.status_code == 200

    async def test_normal_user_cannot_access_knowledge(self, client, user_headers):
        """普通用户访问知识库管理应返回 403。"""
        resp = await client.get("/api/knowledge/stats", headers=user_headers)
        assert resp.status_code == 403

    async def test_normal_user_can_access_chat(self, client, user_headers):
        """普通用户应能访问聊天功能。"""
        resp = await client.get("/api/chat/sessions", headers=user_headers)
        assert resp.status_code == 200


class TestUserProfile:
    """用户资料测试。"""

    async def test_get_profile(self, client, user_headers):
        """应返回当前用户资料。"""
        resp = await client.get("/api/user/profile", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"
