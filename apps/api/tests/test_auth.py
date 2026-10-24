from datetime import timedelta

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from app.core.auth import required_role
from app.core.config import Settings, settings
from app.models import AuditEvent, AuthSession, LinkSubmission, User, utcnow
from app.schemas.auth import UserCreate
from app.services.auth import create_user

OWNER_PASSWORD = "owner-test-password-123"
RESEARCHER_PASSWORD = "researcher-password-123"
VIEWER_PASSWORD = "viewer-test-password-123"


def enable_auth(monkeypatch, *, secure: bool = False) -> None:
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "auth_cookie_secure", secure)


def add_user(db, *, email: str, password: str, role: str) -> User:
    return create_user(
        db,
        UserCreate(name=role.title(), email=email, password=password, role=role),
        actor="test-operator",
    )


def login(client, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def csrf(client) -> str:
    value = client.cookies.get(settings.auth_csrf_cookie_name)
    assert value
    return value


def test_trusted_local_mode_preserves_owner_workflow(client):
    config = client.get("/api/v1/auth/config")
    me = client.get("/api/v1/auth/me")

    assert config.json() == {
        "enabled": False,
        "mode": "disabled",
        "csrf_cookie_name": "research_csrf",
    }
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "owner"
    assert client.get("/api/v1/research").status_code == 200


def test_enabled_auth_requires_login_but_keeps_health_public(client, monkeypatch):
    enable_auth(monkeypatch)

    assert client.get("/api/v1/health").status_code == 200
    protected = client.get("/api/v1/research")

    assert protected.status_code == 401
    assert protected.json()["error"]["code"] == "AUTH_REQUIRED"


def test_login_uses_hashed_password_and_secure_cookie_contract(client, db, monkeypatch):
    enable_auth(monkeypatch, secure=True)
    owner = add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")

    response = login(client, "OWNER@example.com", OWNER_PASSWORD)

    assert response.status_code == 200
    assert response.json()["user"]["id"] == owner.id
    assert owner.password_hash != OWNER_PASSWORD
    set_cookie = response.headers.get_list("set-cookie")
    assert any("HttpOnly" in value and "Secure" in value for value in set_cookie)
    assert all("SameSite=lax" in value for value in set_cookie)
    sessions = list(db.scalars(select(AuthSession)))
    assert len(sessions) == 1
    assert OWNER_PASSWORD not in sessions[0].token_hash
    assert len(sessions[0].token_hash) == 64


def test_invalid_login_is_generic_and_validation_does_not_echo_password(client, db, monkeypatch):
    enable_auth(monkeypatch)
    add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")

    wrong = login(client, "missing@example.com", "wrong-password-value")
    marker = "shortmark"
    invalid = login(client, "owner@example.com", marker)

    assert wrong.status_code == 401
    assert wrong.json()["error"] == {
        "code": "AUTH_REQUIRED",
        "message": "Bạn cần đăng nhập để tiếp tục.",
    }
    assert invalid.status_code == 422
    assert marker not in invalid.text


def test_login_attempts_have_a_typed_rate_limit(client, monkeypatch):
    enable_auth(monkeypatch)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_login_attempts_per_window", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    first = login(client, "missing@example.com", "wrong-password-value")
    second = login(client, "missing@example.com", "wrong-password-value")
    limited = login(client, "missing@example.com", "wrong-password-value")

    assert first.status_code == second.status_code == 401
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert limited.headers["Retry-After"] == "60"


def test_csrf_is_required_and_authenticated_actor_reaches_audit(client, db, monkeypatch):
    enable_auth(monkeypatch)
    owner = add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")
    assert login(client, owner.email, OWNER_PASSWORD).status_code == 200
    payload = {
        "title": "Authenticated research",
        "type": "reference",
        "collection_method": "manual",
        "content": "Bounded authenticated content.",
    }

    rejected = client.post("/api/v1/research", json=payload)
    created = client.post(
        "/api/v1/research",
        json=payload,
        headers={"X-CSRF-Token": csrf(client)},
    )

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "CSRF_REQUIRED"
    assert created.status_code == 201
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == created.json()["id"],
            AuditEvent.action == "research.created",
        )
    )
    assert event is not None
    assert event.actor == owner.id


@pytest.mark.parametrize(
    ("role", "read_status", "write_status", "owner_status"),
    [
        ("viewer", 200, 403, 403),
        ("researcher", 200, 201, 403),
        ("owner", 200, 201, 404),
    ],
)
def test_role_hierarchy_is_enforced_server_side(
    client, db, monkeypatch, role, read_status, write_status, owner_status
):
    enable_auth(monkeypatch)
    password = {
        "viewer": VIEWER_PASSWORD,
        "researcher": RESEARCHER_PASSWORD,
        "owner": OWNER_PASSWORD,
    }[role]
    user = add_user(db, email=f"{role}@example.com", password=password, role=role)
    assert login(client, user.email, password).status_code == 200
    token = csrf(client)

    read = client.get("/api/v1/research")
    write = client.post(
        "/api/v1/research",
        json={
            "title": f"{role} draft",
            "type": "reference",
            "collection_method": "manual",
            "content": "Role policy fixture.",
        },
        headers={"X-CSRF-Token": token},
    )
    owner_only = client.post(
        "/api/v1/graph/change-sets/missing/apply",
        headers={"X-CSRF-Token": token},
    )

    assert read.status_code == read_status
    assert write.status_code == write_status
    assert owner_only.status_code == owner_status


def test_owner_can_create_user_and_deactivation_revokes_sessions(client, db, monkeypatch):
    enable_auth(monkeypatch)
    owner = add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")
    assert login(client, owner.email, OWNER_PASSWORD).status_code == 200
    owner_csrf = csrf(client)
    created = client.post(
        "/api/v1/auth/users",
        json={
            "name": "Viewer",
            "email": "viewer@example.com",
            "role": "viewer",
            "password": VIEWER_PASSWORD,
        },
        headers={"X-CSRF-Token": owner_csrf},
    )
    assert created.status_code == 201
    assert VIEWER_PASSWORD not in created.text
    assert created.json()["password_configured"] is True

    client.cookies.clear()
    assert login(client, "viewer@example.com", VIEWER_PASSWORD).status_code == 200
    viewer_session = db.scalar(
        select(AuthSession)
        .join(User, User.id == AuthSession.user_id)
        .where(User.email == "viewer@example.com", AuthSession.revoked_at.is_(None))
    )
    assert viewer_session is not None

    client.cookies.clear()
    assert login(client, owner.email, OWNER_PASSWORD).status_code == 200
    disabled = client.patch(
        f"/api/v1/auth/users/{created.json()['id']}",
        json={"active": False},
        headers={"X-CSRF-Token": csrf(client)},
    )

    assert disabled.status_code == 200
    db.refresh(viewer_session)
    assert viewer_session.revoked_at is not None


def test_expired_session_and_logout_are_revoked(client, db, monkeypatch):
    enable_auth(monkeypatch)
    owner = add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")
    assert login(client, owner.email, OWNER_PASSWORD).status_code == 200
    record = db.scalar(select(AuthSession).where(AuthSession.revoked_at.is_(None)))
    assert record is not None
    record.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    assert client.get("/api/v1/auth/me").status_code == 401

    client.cookies.clear()
    assert login(client, owner.email, OWNER_PASSWORD).status_code == 200
    active = db.scalar(
        select(AuthSession)
        .where(AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.created_at.desc())
    )
    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf(client)})

    assert response.status_code == 204
    db.refresh(active)
    assert active.revoked_at is not None


def test_route_policy_matrix_covers_read_query_write_and_owner_operations():
    assert required_role("GET", "/api/v1/documents") == "viewer"
    assert required_role("POST", "/api/v1/search/semantic") == "viewer"
    assert required_role("POST", "/api/v1/documents") == "researcher"
    assert required_role("POST", "/api/v1/documents/edit-in-place") == "researcher"
    assert required_role("POST", "/api/v1/documents/workspace/graph/research") == "researcher"
    assert required_role("DELETE", "/api/v1/documents/workspace") == "owner"
    assert required_role("DELETE", "/api/v1/research/item") == "owner"
    assert required_role("POST", "/api/v1/ingestion/links/item/approve") == "owner"
    assert required_role("POST", "/api/v1/graph/change-sets/set/apply") == "owner"
    assert required_role("POST", "/api/v1/graph/rebuild") == "owner"
    assert required_role("POST", "/api/v1/search/rebuild") == "owner"


def test_secret_files_override_environment_values(tmp_path):
    (tmp_path / "openai_api_key").write_text("file-secret-marker\n", encoding="utf-8")

    configured = Settings(
        _env_file=None,
        secret_files_dir=str(tmp_path),
        openai_api_key=SecretStr("environment-marker"),
    )

    assert configured.openai_api_key is not None
    assert configured.openai_api_key.get_secret_value() == "file-secret-marker"


def test_non_local_deployment_fails_closed_without_secure_auth():
    with pytest.raises(ValidationError, match="AUTH_MODE=local"):
        Settings(
            _env_file=None,
            deployment_environment="production",
            auth_mode="disabled",
        )
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            deployment_environment="production",
            auth_mode="local",
            auth_cookie_secure=False,
            auth_cookie_name="__Host-research_session",
        )
    with pytest.raises(ValidationError, match="__Host-"):
        Settings(
            _env_file=None,
            deployment_environment="production",
            auth_mode="local",
            auth_cookie_secure=True,
            auth_cookie_name="research_session",
        )


def test_member_changes_own_password_and_other_sessions_are_revoked(
    client, db, monkeypatch
):
    enable_auth(monkeypatch)
    viewer = add_user(db, email="viewer@example.com", password=VIEWER_PASSWORD, role="viewer")
    # An older session on another device must be signed out by the change.
    assert login(client, viewer.email, VIEWER_PASSWORD).status_code == 200
    other_device = db.scalar(select(AuthSession).where(AuthSession.user_id == viewer.id))
    client.cookies.clear()
    assert login(client, viewer.email, VIEWER_PASSWORD).status_code == 200
    new_password = "viewer-new-password-456"

    missing_csrf = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": VIEWER_PASSWORD, "new_password": new_password},
    )
    wrong = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": "not-the-password", "new_password": new_password},
        headers={"X-CSRF-Token": csrf(client)},
    )
    changed = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": VIEWER_PASSWORD, "new_password": new_password},
        headers={"X-CSRF-Token": csrf(client)},
    )

    assert missing_csrf.status_code == 403
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "PASSWORD_INCORRECT"
    assert changed.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 200
    db.refresh(other_device)
    assert other_device.revoked_at is not None
    client.cookies.clear()
    assert login(client, viewer.email, VIEWER_PASSWORD).status_code == 401
    assert login(client, viewer.email, new_password).status_code == 200
    actions = set(db.scalars(select(AuditEvent.action)))
    assert {"auth.password.change_failed", "auth.password.changed"} <= actions


def test_password_change_is_unavailable_in_trusted_local_mode(client):
    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": "anything-at-all", "new_password": "new-password-value"},
    )

    assert response.status_code == 409


DECISION_SEGMENTS = {
    "approve",
    "reject",
    "apply",
    "compensate",
    "accept",
    "rebuild",
    "bulk-review",
    "decision",
    "edit-and-approve",
}
# Thao tác soạn thảo tài liệu của chính nhà nghiên cứu, không xuất bản vào kho tri thức chung.
RESEARCHER_DECISION_ALLOWLIST = {
    "/api/v1/documents/{document_id}/ai-edits/{proposal_id}/accept",
    "/api/v1/documents/{document_id}/ai-edits/{proposal_id}/reject",
    "/api/v1/documents/{document_id}/rag/rebuild",
}


def test_every_review_or_publish_route_requires_owner():
    from app.main import app

    checked = 0
    for path, operations in app.openapi()["paths"].items():
        last_segment = path.rstrip("/").rsplit("/", 1)[-1]
        if last_segment not in DECISION_SEGMENTS or path in RESEARCHER_DECISION_ALLOWLIST:
            continue
        concrete = path.replace("{", "").replace("}", "")
        for method in {method.upper() for method in operations} - {"GET", "HEAD", "OPTIONS"}:
            checked += 1
            assert required_role(method, concrete) == "owner", (method, path)
    assert checked >= 15


def test_researcher_cannot_publish_through_side_doors(client, db, monkeypatch):
    enable_auth(monkeypatch)
    add_user(db, email="researcher@example.com", password=RESEARCHER_PASSWORD, role="researcher")
    assert login(client, "researcher@example.com", RESEARCHER_PASSWORD).status_code == 200
    headers = {"X-CSRF-Token": csrf(client)}

    bulk = client.post(
        "/api/v1/ingestion/links/bulk-review", json={"decision": "approve"}, headers=headers
    )
    source = client.post(
        "/api/v1/collector/sources",
        json={
            "key": "feed",
            "name": "Feed",
            "url": "https://example.com/feed.xml",
            "type": "rss",
            "auto_approve_threshold": 0,
        },
        headers=headers,
    )
    submitted = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/paper", "auto_approve": True},
        headers=headers,
    )

    assert bulk.status_code == 403
    assert source.status_code == 403
    assert submitted.status_code == 202
    stored = db.get(LinkSubmission, submitted.json()["id"])
    assert stored.auto_approve is False


def test_researcher_cannot_rewrite_approved_research(client, db, monkeypatch):
    enable_auth(monkeypatch)
    add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")
    add_user(db, email="researcher@example.com", password=RESEARCHER_PASSWORD, role="researcher")
    assert login(client, "owner@example.com", OWNER_PASSWORD).status_code == 200
    owner_headers = {"X-CSRF-Token": csrf(client)}
    created = client.post(
        "/api/v1/research",
        json={"title": "Agent memory", "content": "Original vetted content"},
        headers=owner_headers,
    ).json()
    for action in ("submit-review", "approve"):
        response = client.post(f"/api/v1/research/{created['id']}/{action}", headers=owner_headers)
        assert response.status_code == 200
    client.cookies.clear()
    assert login(client, "researcher@example.com", RESEARCHER_PASSWORD).status_code == 200

    response = client.put(
        f"/api/v1/research/{created['id']}",
        json={"content": "Unreviewed replacement"},
        headers={"X-CSRF-Token": csrf(client)},
    )
    comment = client.post(
        f"/api/v1/research/{created['id']}/comments",
        json={"body": "Cần thêm nguồn", "author": "Spoofed Owner"},
        headers={"X-CSRF-Token": csrf(client)},
    )

    assert response.status_code == 403
    assert comment.status_code == 201
    assert comment.json()["author"] == "Researcher"


def test_rate_limits_are_per_member_not_shared_behind_the_proxy(client, db, monkeypatch):
    enable_auth(monkeypatch)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_chat_per_window", 1)
    add_user(db, email="first@example.com", password=VIEWER_PASSWORD, role="viewer")
    add_user(db, email="second@example.com", password=VIEWER_PASSWORD, role="viewer")

    def search_twice(email: str) -> list[int]:
        client.cookies.clear()
        assert login(client, email, VIEWER_PASSWORD).status_code == 200
        headers = {"X-CSRF-Token": csrf(client)}
        return [
            client.post(
                "/api/v1/search/semantic", json={"query": "agent memory"}, headers=headers
            ).status_code
            for _ in range(2)
        ]

    first = search_twice("first@example.com")
    second = search_twice("second@example.com")

    assert first[1] == 429
    assert second[0] != 429


def test_repeated_wrong_passwords_lock_only_that_account_briefly(client, db, monkeypatch):
    enable_auth(monkeypatch)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_login_attempts_per_window", 3)
    # Bỏ giới hạn theo IP để chỉ kiểm tra giới hạn số lần sai theo tài khoản.
    monkeypatch.setattr("app.core.runtime_controls._rate_policy", lambda _request: None)
    add_user(db, email="owner@example.com", password=OWNER_PASSWORD, role="owner")
    add_user(db, email="viewer@example.com", password=VIEWER_PASSWORD, role="viewer")

    wrong = [login(client, "owner@example.com", "not-the-password").status_code for _ in range(3)]
    locked = login(client, "OWNER@example.com", OWNER_PASSWORD)
    other_account = login(client, "viewer@example.com", VIEWER_PASSWORD)

    assert wrong == [401, 401, 401]
    assert locked.status_code == 429
    assert other_account.status_code == 200
