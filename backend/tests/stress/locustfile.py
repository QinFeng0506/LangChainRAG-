"""RAG 知识库问答系统 — Locust 压力测试主入口。

用法：
    # 默认模式：仅 RAG 核心场景（推荐）
    locust -f tests/stress/locustfile.py --host http://localhost:8000

    # 专项场景：健康检查基线
    locust -f tests/stress/locustfile.py --host http://localhost:8000 --tags health

    # 专项场景：登录风暴
    locust -f tests/stress/locustfile.py --host http://localhost:8000 --tags login

    # 专项场景：缓存命中
    locust -f tests/stress/locustfile.py --host http://localhost:8000 --tags cache_hit

    # 专项场景：知识库上传
    locust -f tests/stress/locustfile.py --host http://localhost:8000 --tags upload

    # 无头模式
    locust -f tests/stress/locustfile.py \
        --headless --users 100 --spawn-rate 5 --run-time 10m \
        --host http://localhost:8000 \
        --html reports/result.html
"""

import json
import random
import os
import itertools
from locust import HttpUser, task, between, events, tag

# ===== 配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")
TEST_USER_PASSWORD = "LoadTest@123"

# 用户编号轮转器（确保每个虚拟用户拿到不同的账号）
_user_counter = itertools.cycle(range(1, 101))


def _load_questions():
    q_path = os.path.join(BASE_DIR, "questions.json")
    if os.path.exists(q_path):
        with open(q_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("hot_questions", []), data.get("cold_questions", [])
    return [], []


HOT_QUESTIONS, COLD_QUESTIONS = _load_questions()

if not HOT_QUESTIONS:
    HOT_QUESTIONS = [
        "iPhone 15 的电池续航怎么样？",
        "这个手机支持5G网络吗？",
        "退换货的有效期是多久？",
        "这款产品的保修期是多长时间？",
        "支持哪些支付方式？",
        "有什么优惠活动吗？",
        "发货需要多长时间？",
        "这款电脑适合办公用吗？",
    ]

if not COLD_QUESTIONS:
    COLD_QUESTIONS = [
        "华为Mate 60 Pro和小米14 Ultra哪个拍照更好？",
        "这款笔记本电脑适合打游戏吗？",
        "我想买一台性价比高的空调，有什么推荐？",
        "索尼WH-1000XM5和AirPods Pro 2哪个降噪更好？",
        "有没有适合学生用的平板电脑？",
        "戴森吸尘器和追觅吸尘器哪个更好用？",
        "这个充电宝能带上飞机吗？",
        "这款防晒霜适合敏感肌吗？",
        "可以分期付款吗？",
    ]


# ===================================================================
# 默认场景：RAG 核心问答（fixed_count > 0，无需 --tags 即运行）
# ===================================================================

class RAGUser(HttpUser):
    """默认场景：登录 → 取会话 → 发 RAG 问题。所有虚拟用户使用不同账号。"""

    wait_time = between(3, 10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.session_ids: list[str] = []

    def on_start(self):
        self.user_index = next(_user_counter)
        username = f"stresstest{self.user_index:03d}"

        # 登录（失败则自动注册）
        with self.client.post(
            "/api/auth/login",
            json={"username": username, "password": TEST_USER_PASSWORD},
            catch_response=True,
            name="POST /api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                self.token = resp.json().get("access_token", "")
                resp.success()
            elif resp.status_code == 401:
                self._register_and_login(username)
                resp.success()
            else:
                resp.failure(f"登录失败 HTTP {resp.status_code}")

        if self.token:
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            self._ensure_session()

    def _register_and_login(self, username: str):
        with self.client.post(
            "/api/auth/register",
            json={"username": username, "password": TEST_USER_PASSWORD,
                  "password_confirm": TEST_USER_PASSWORD},
            catch_response=True,
            name="POST /api/auth/register",
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
                login_resp = self.client.post(
                    "/api/auth/login",
                    json={"username": username, "password": TEST_USER_PASSWORD},
                    name="POST /api/auth/login",
                )
                if login_resp.status_code == 200:
                    self.token = login_resp.json().get("access_token", "")
                    if self.token:
                        self.client.headers.update(
                            {"Authorization": f"Bearer {self.token}"})
            else:
                resp.failure(f"注册失败 HTTP {resp.status_code}")

    def _ensure_session(self):
        """确保至少有一个可用会话。"""
        with self.client.get(
            "/api/chat/sessions",
            catch_response=True,
            name="GET /api/chat/sessions",
        ) as resp:
            if resp.status_code == 200:
                sessions = resp.json()
                self.session_ids = [s["id"] for s in sessions]
                resp.success()
            else:
                resp.failure(f"获取会话列表失败 HTTP {resp.status_code}")

        if not self.session_ids:
            with self.client.post(
                "/api/chat/sessions",
                json={"title": "压测会话"},
                catch_response=True,
                name="POST /api/chat/sessions",
            ) as resp:
                if resp.status_code == 201:
                    self.session_ids.append(resp.json()["id"])
                    resp.success()
                else:
                    resp.failure(f"创建会话失败 HTTP {resp.status_code}")

    @task(5)
    def ask_question(self):
        """核心：发送 RAG 问答请求。"""
        if not self.token or not self.session_ids:
            return

        session_id = random.choice(self.session_ids)
        question = random.choice(COLD_QUESTIONS + HOT_QUESTIONS)

        with self.client.post(
            "/api/chat/query",
            json={"session_id": session_id, "question": question},
            catch_response=True,
            stream=True,
            name="POST /api/chat/query",
        ) as resp:
            if resp.status_code == 429:
                resp.success()
                return
            if resp.status_code != 200:
                resp.failure(f"查询失败 HTTP {resp.status_code}")
                return
            # 读完 SSE 流
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    try:
                        evt = json.loads(line[6:])
                        if evt.get("type") == "error":
                            resp.failure(f"RAG错误: {evt.get('content','')}")
                            return
                        if evt.get("type") == "done":
                            break
                    except json.JSONDecodeError:
                        pass
            resp.success()

    @task(2)
    def browse_sessions(self):
        """浏览会话列表。"""
        if not self.token:
            return
        with self.client.get(
            "/api/chat/sessions",
            catch_response=True,
            name="GET /api/chat/sessions",
        ) as resp:
            if resp.status_code == 200:
                self.session_ids = [s["id"] for s in resp.json()]
                resp.success()
            else:
                resp.failure(f"失败 HTTP {resp.status_code}")

    @task(1)
    def read_history(self):
        """查看历史消息。"""
        if not self.token or not self.session_ids:
            return
        sid = random.choice(self.session_ids)
        with self.client.get(
            f"/api/chat/sessions/{sid}/messages",
            catch_response=True,
            name="GET /api/chat/sessions/{id}/messages",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"失败 HTTP {resp.status_code}")


# ===================================================================
# 专项场景（fixed_count=0，需要 --tags 才会运行）
# ===================================================================

class HealthCheckUser(HttpUser):
    """场景1: 健康检查基线。用法: --tags health"""
    fixed_count = 0
    wait_time = between(0.1, 0.5)

    @task
    @tag("health")
    def check_health(self):
        with self.client.get("/api/health", catch_response=True, name="GET /api/health") as resp:
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                resp.success()
            else:
                resp.failure("失败")


class LoginStormUser(HttpUser):
    """场景2: 登录风暴。用法: --tags login"""
    fixed_count = 0
    wait_time = between(0.5, 2)

    @task
    @tag("login")
    def login(self):
        idx = random.randint(1, 100)
        username = f"stresstest{idx:03d}"
        with self.client.post(
            "/api/auth/login",
            json={"username": username, "password": TEST_USER_PASSWORD},
            catch_response=True,
            name="POST /api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                # 自动注册
                reg = self.client.post("/api/auth/register", json={
                    "username": username, "password": TEST_USER_PASSWORD,
                    "password_confirm": TEST_USER_PASSWORD,
                }, name="POST /api/auth/register")
                if reg.status_code in (200, 201):
                    resp2 = self.client.post("/api/auth/login", json={
                        "username": username, "password": TEST_USER_PASSWORD,
                    }, name="POST /api/auth/login")
                    if resp2.status_code == 200:
                        resp2.success()
                    else:
                        resp2.failure(f"重登录失败 HTTP {resp2.status_code}")
            else:
                resp.failure(f"失败 HTTP {resp.status_code}")


class CacheHitUser(HttpUser):
    """场景3: 缓存命中。用法: --tags cache_hit"""
    fixed_count = 0
    wait_time = between(2, 6)

    def on_start(self):
        idx = next(_user_counter)
        username = f"stresstest{idx:03d}"
        resp = self.client.post("/api/auth/login", json={
            "username": username, "password": TEST_USER_PASSWORD,
        }, name="POST /api/auth/login")
        if resp.status_code == 401:
            self.client.post("/api/auth/register", json={
                "username": username, "password": TEST_USER_PASSWORD,
                "password_confirm": TEST_USER_PASSWORD,
            }, name="POST /api/auth/register")
            resp = self.client.post("/api/auth/login", json={
                "username": username, "password": TEST_USER_PASSWORD,
            }, name="POST /api/auth/login")
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            # 获取或创建会话
            sr = self.client.get("/api/chat/sessions", name="GET /api/chat/sessions")
            self.sid = None
            if sr.status_code == 200:
                sessions = sr.json()
                self.sid = sessions[0]["id"] if sessions else None
            if not self.sid:
                cr = self.client.post("/api/chat/sessions",
                    json={"title": "缓存测试"}, name="POST /api/chat/sessions")
                if cr.status_code == 201:
                    self.sid = cr.json()["id"]

    @task
    @tag("cache_hit")
    def ask_hot(self):
        if not getattr(self, "sid", None):
            return
        q = random.choice(HOT_QUESTIONS)
        with self.client.post("/api/chat/query",
            json={"session_id": self.sid, "question": q},
            catch_response=True, stream=True,
            name="POST /api/chat/query (cache)",
        ) as resp:
            if resp.status_code in (200, 429):
                for _ in resp.iter_lines():
                    pass
                resp.success()
            else:
                resp.failure(f"失败 HTTP {resp.status_code}")


class KnowledgeUploadUser(HttpUser):
    """场景6: 知识库上传。用法: --tags upload"""
    fixed_count = 0
    wait_time = between(5, 15)

    def on_start(self):
        resp = self.client.post("/api/auth/login", json={
            "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
        }, name="POST /api/auth/login (admin)")
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task
    @tag("upload")
    def upload(self):
        if not getattr(self, "token", None):
            return
        content = f"压测文档 - 商品{random.randint(1,9999)} - 价格{random.randint(99,9999)}元\n"
        files = {"file": (f"stress_{random.randint(1,9999)}.txt",
                          content.encode("utf-8"), "text/plain")}
        with self.client.post("/api/knowledge/upload", files=files,
            catch_response=True, name="POST /api/knowledge/upload") as resp:
            if resp.status_code in (200, 201, 413):
                resp.success()
            else:
                resp.failure(f"失败 HTTP {resp.status_code}")
