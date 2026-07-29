"""聊天会话测试 —— 会话 CRUD、历史消息、权限隔离。"""
import pytest
from uuid import uuid4


class TestSessionCRUD:
    """会话管理测试。"""

    async def test_create_session(self, client, user_headers):
        """创建会话应返回会话记录。"""
        resp = await client.post("/api/chat/sessions", headers=user_headers, json={"title": "测试会话"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "测试会话"
        assert "id" in data

    async def test_create_session_default_title(self, client, user_headers):
        """不传标题时应默认为'新会话'。"""
        resp = await client.post("/api/chat/sessions", headers=user_headers, json={})
        assert resp.status_code == 201
        assert resp.json()["title"] == "新会话"

    async def test_list_sessions(self, client, user_headers):
        """列出用户的所有会话。"""
        for i in range(3):
            await client.post("/api/chat/sessions", headers=user_headers, json={"title": f"会话{i}"})

        resp = await client.get("/api/chat/sessions", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # 按更新时间倒序
        titles = [s["title"] for s in data]
        assert "会话2" in titles

    async def test_list_sessions_empty(self, client, user_headers):
        """无会话时应返回空列表。"""
        resp = await client.get("/api/chat/sessions", headers=user_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_rename_session(self, client, user_headers):
        """重命名会话应成功更新标题。"""
        create_resp = await client.post("/api/chat/sessions", headers=user_headers, json={"title": "旧标题"})
        session_id = create_resp.json()["id"]

        resp = await client.patch(f"/api/chat/sessions/{session_id}", headers=user_headers, json={"title": "新标题"})
        assert resp.status_code == 200

        # 验证标题已更新
        list_resp = await client.get("/api/chat/sessions", headers=user_headers)
        assert list_resp.json()[0]["title"] == "新标题"

    async def test_delete_session(self, client, user_headers):
        """删除会话应成功且不再出现在列表中。"""
        create_resp = await client.post("/api/chat/sessions", headers=user_headers, json={})
        session_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/chat/sessions/{session_id}", headers=user_headers)
        assert resp.status_code == 200

        list_resp = await client.get("/api/chat/sessions", headers=user_headers)
        assert len(list_resp.json()) == 0

    async def test_delete_nonexistent_session(self, client, user_headers):
        """删除不存在的会话应返回 404。"""
        resp = await client.delete("/api/chat/sessions/fake-id", headers=user_headers)
        assert resp.status_code == 404

    async def test_no_auth(self, client):
        """未登录操作应返回 401。"""
        resp = await client.get("/api/chat/sessions")
        assert resp.status_code == 401


class TestSessionIsolation:
    """多用户会话隔离测试。"""

    async def test_users_cannot_see_each_others_sessions(self, client):
        """用户 A 不应看到用户 B 的会话。"""
        # 使用唯一用户名避免与其他测试冲突
        from uuid import uuid4
        name_a = f"ua_{uuid4().hex[:6]}"
        name_b = f"ub_{uuid4().hex[:6]}"

        await client.post("/api/auth/register", json={"username": name_a, "password": "passA123"})
        await client.post("/api/auth/register", json={"username": name_b, "password": "passB123"})

        login_a = await client.post("/api/auth/login", json={"username": name_a, "password": "passA123"})
        login_b = await client.post("/api/auth/login", json={"username": name_b, "password": "passB123"})

        # 分别登录（使用已注册的唯一用户名）
        login_a = await client.post("/api/auth/login", json={"username": name_a, "password": "passA123"})
        login_b = await client.post("/api/auth/login", json={"username": name_b, "password": "passB123"})

        token_a = login_a.json()["access_token"]
        token_b = login_b.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # A 创建会话
        await client.post("/api/chat/sessions", headers=headers_a, json={"title": "A-private"})

        # B 看不到 A 的会话
        resp_b = await client.get("/api/chat/sessions", headers=headers_b)
        assert len(resp_b.json()) == 0

        # A 能看到自己的会话
        resp_a = await client.get("/api/chat/sessions", headers=headers_a)
        assert len(resp_a.json()) == 1
        assert resp_a.json()[0]["title"] == "A-private"

    async def test_cannot_access_others_session(self, client):
        """用户不应访问他人的会话消息。"""
        from uuid import uuid4
        owner_name = f"owner_{uuid4().hex[:6]}"
        intruder_name = f"intruder_{uuid4().hex[:6]}"

        # 创建用户 A 和会话
        await client.post("/api/auth/register", json={"username": owner_name, "password": "pass123"})
        login = await client.post("/api/auth/login", json={"username": owner_name, "password": "pass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/chat/sessions", headers=headers, json={"title": "私有会话"})
        session_id = create.json()["id"]

        # 创建用户 B，尝试访问 A 的会话
        await client.post("/api/auth/register", json={"username": intruder_name, "password": "bad123"})
        login_b = await client.post("/api/auth/login", json={"username": intruder_name, "password": "bad123"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        resp = await client.get(f"/api/chat/sessions/{session_id}/messages", headers=headers_b)
        assert resp.status_code == 404


class TestChatMessages:
    """聊天消息测试。"""

    async def _create_session(self, client, headers, title="测试"):
        resp = await client.post("/api/chat/sessions", headers=headers, json={"title": title})
        return resp.json()["id"]

    async def test_empty_messages(self, client, user_headers):
        """无消息的会话应返回空列表。"""
        sid = await self._create_session(client, user_headers)
        resp = await client.get(f"/api/chat/sessions/{sid}/messages", headers=user_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_messages_not_found_session(self, client, user_headers):
        """请求不存在会话的消息应返回 404。"""
        resp = await client.get("/api/chat/sessions/fake-id/messages", headers=user_headers)
        assert resp.status_code == 404

    async def test_rename_empty_title(self, client, user_headers):
        """重命名为空标题应返回 422。"""
        sid = await self._create_session(client, user_headers)
        resp = await client.patch(f"/api/chat/sessions/{sid}", headers=user_headers, json={"title": ""})
        assert resp.status_code == 422

    async def test_create_session_too_long_title(self, client, user_headers):
        """过长标题应返回 422。"""
        resp = await client.post("/api/chat/sessions", headers=user_headers, json={"title": "x" * 250})
        assert resp.status_code == 422


class TestChatQuery:
    """RAG 问答接口测试。"""

    async def _create_session(self, client, headers):
        resp = await client.post("/api/chat/sessions", headers=headers, json={})
        return resp.json()["id"]

    async def test_query_no_auth(self, client):
        """未登录提问应返回 401。"""
        resp = await client.post("/api/chat/query", json={"session_id": "any", "question": "测试问题"})
        assert resp.status_code == 401

    async def test_query_blank_question(self, client, user_headers):
        """空问题应返回 422。"""
        sid = await self._create_session(client, user_headers)
        resp = await client.post("/api/chat/query", headers=user_headers, json={
            "session_id": sid, "question": ""
        })
        assert resp.status_code == 422

    async def test_query_nonexistent_session(self, client, user_headers):
        """不存在的会话应返回 404。"""
        resp = await client.post("/api/chat/query", headers=user_headers, json={
            "session_id": "nonexistent", "question": "测试"
        })
        assert resp.status_code == 404

    async def test_query_others_session(self, client):
        """不能在他人的会话中提问。"""
        # A 创建会话
        uid_a = f"qa{uuid4().hex[:6]}"
        uid_b = f"qb{uuid4().hex[:6]}"

        await client.post("/api/auth/register", json={"username": uid_a, "password": "pass123"})
        login_a = await client.post("/api/auth/login", json={"username": uid_a, "password": "pass123"})
        token_a = login_a.json()["access_token"]
        sid = await self._create_session(client, {"Authorization": f"Bearer {token_a}"})

        # B 尝试在 A 的会话中提问
        await client.post("/api/auth/register", json={"username": uid_b, "password": "pass123"})
        login_b = await client.post("/api/auth/login", json={"username": uid_b, "password": "pass123"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        resp = await client.post("/api/chat/query", headers=headers_b, json={
            "session_id": sid, "question": "恶意提问"
        })
        assert resp.status_code == 404
