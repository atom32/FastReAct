from fastapi.testclient import TestClient

from fastreact.adapters import gateway


class FakeAgentSession:
    def __init__(self):
        import asyncio

        self._message_queue = asyncio.Queue(maxsize=5)

    def update_activity(self):
        pass

    def interrupt(self):
        pass

    async def enqueue_message(self, message):
        await self._message_queue.put(message)
        return True

    async def process_message(self, message, on_event):
        return None


class FakeSessions:
    def list(self, user_key=None):
        return [{"session_id": "s1", "user_key": user_key or "web:test", "status": "idle"}]

    def create(self, **kwargs):
        return FakeAgentSession()

    def detail(self, session_id):
        if session_id != "s1":
            return None
        return {"session_id": "s1", "status": "idle", "events": [{"type": "session_start"}]}


class FakeStore:
    def __init__(self):
        self.records = {
            "traces": [{"session_id": "s1", "time_to_final_ms": 10}],
            "audit": [{"session_id": "s1", "tool_name": "read_file"}],
        }

    def read(self, stream, limit=200, **filters):
        records = self.records.get(stream, [])
        return [record for record in records if all(record.get(k) == v for k, v in filters.items() if v is not None)]

    def append(self, stream, record):
        self.records.setdefault(stream, []).append(record)
        return record


class FakeTasks:
    def __init__(self):
        self.task = {"task_id": "task-1", "title": "demo", "status": "pending"}

    def list(self, **kwargs):
        return [self.task]

    def create(self, **kwargs):
        self.task = {"task_id": "task-2", "title": kwargs["title"], "status": "pending"}
        return self.task

    def update(self, task_id, **kwargs):
        self.task.update(kwargs)
        return self.task


class FakeToolExecutor:
    def list_approvals(self):
        return [{"request_id": "approval-1", "tool_name": "exec", "status": "pending"}]

    def resolve_approval(self, request_id, approved, reason=""):
        return request_id == "approval-1"


class FakeAgent:
    def __init__(self):
        self.sessions = FakeSessions()
        self.store = FakeStore()
        self.tasks = FakeTasks()
        self.tool_executor = FakeToolExecutor()

    def list_tools(self):
        return ["read_file", "task_create"]

    def list_mcp_tools(self):
        return []

    def list_tool_schema_summary(self):
        return [{"name": "read_file", "description": "Read", "parameters": ["path"]}]

    def list_mcp_server_status(self):
        return [{"name": "demo", "alive": True}]

    def register_temp_user_if_needed(self, user_key):
        return user_key.startswith("web:temp_")

    async def ensure_mcp_loaded(self, required_skills=None):
        return {}

    @property
    def config(self):
        class Paths:
            global_skills_dir = "/tmp/skills"

        class Config:
            paths = Paths()

        return Config()


def test_gateway_control_plane_apis(monkeypatch):
    fake = FakeAgent()
    monkeypatch.setattr(gateway, "get_gateway_agent", lambda config=None: fake)
    app = gateway.create_gateway_app()
    client = TestClient(app)

    assert client.get("/api/sessions").json()["count"] == 1
    detail = client.get("/api/sessions/s1").json()
    assert detail["traces"]
    assert detail["audit"]
    assert detail["tasks"]

    created = client.post("/api/tasks", json={"title": "new task"}).json()
    assert created["title"] == "new task"
    updated = client.patch("/api/tasks/task-2", json={"status": "completed"}).json()
    assert updated["status"] == "completed"

    assert client.get("/api/audit").json()["count"] == 1
    assert client.get("/api/traces").json()["count"] == 1
    assert client.get("/api/control/pending-approvals").json()["count"] == 1
    assert client.post("/api/control/tool-approval", json={"request_id": "approval-1", "approved": True}).json()["ok"]

    tools = client.get("/api/tools").json()
    assert tools["schemas"][0]["name"] == "read_file"
    assert tools["mcp_servers"][0]["alive"] is True


def test_gateway_control_plane_optional_admin_auth(monkeypatch):
    fake = FakeAgent()
    monkeypatch.setattr(gateway, "get_gateway_agent", lambda config=None: fake)
    monkeypatch.setenv("FASTREACT_ADMIN_API_AUTH", "true")
    monkeypatch.setenv("GATEWAY_ADMIN_KEY", "test-admin-key")
    gateway.ADMIN_API_KEY = None

    app = gateway.create_gateway_app()
    client = TestClient(app)

    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/sessions", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/api/sessions", headers={"X-Admin-Key": "test-admin-key"}).json()["count"] == 1
    assert client.post(
        "/api/tasks",
        json={"title": "secured task"},
        headers={"X-Admin-Key": "test-admin-key"},
    ).json()["title"] == "secured task"

    gateway.ADMIN_API_KEY = None


def test_gateway_websocket_disconnect_is_graceful(monkeypatch):
    fake = FakeAgent()
    monkeypatch.setattr(gateway, "get_gateway_agent", lambda config=None: fake)
    app = gateway.create_gateway_app()
    client = TestClient(app)

    with client.websocket_connect("/ws?user_key=web:e2e") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json()["type"] == "pong"
