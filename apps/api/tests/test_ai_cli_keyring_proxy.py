import pytest

from app.ai_cli_keyring_proxy import KeyringDenied, KeyringPolicy

ALLOWED = "/org/freedesktop/secrets/collection/login/1"
OTHER = "/org/freedesktop/secrets/collection/login/2"


def test_keyring_rejects_foreign_items_including_mixed_batch():
    policy = KeyringPolicy({ALLOWED})
    policy.require_items([ALLOWED])
    policy.require_items([])
    for paths in ([OTHER], [ALLOWED, OTHER], [ALLOWED + "/../2"]):
        with pytest.raises(KeyringDenied):
            policy.require_items(paths)


def test_keyring_sessions_are_owned_by_this_proxy():
    policy = KeyringPolicy({ALLOWED})
    policy.sessions.add("/session/own")
    policy.require_session("/session/own")
    for session in ("/", "/session/other", ""):
        with pytest.raises(KeyringDenied):
            policy.require_session(session)


@pytest.mark.parametrize(
    "attributes",
    [
        {},
        {"service": "other", "username": "antigravity"},
        {"service": "gemini", "username": "another-user"},
        {"application": "Antigravity"},
        {"service": "gemini", "username": "antigravity", "extra": "arbitrary"},
        {"service": "gemini", "username": "antigravity", "xdg:schema": "another-schema"},
    ],
)
def test_keyring_write_scope_cannot_be_broadened(attributes):
    with pytest.raises(KeyringDenied):
        KeyringPolicy({ALLOWED}).require_attributes(attributes)


def test_keyring_allows_only_original_application_attributes():
    policy = KeyringPolicy({ALLOWED})
    policy.require_attributes({"service": "gemini", "username": "antigravity"})
    policy.require_attributes(
        {
            "service": "gemini",
            "username": "antigravity",
            "xdg:schema": "org.freedesktop.Secret.Generic",
        }
    )
    assert policy.collections == {"/org/freedesktop/secrets/collection/login"}
