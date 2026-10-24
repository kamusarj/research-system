import argparse
import asyncio
import getpass
import json
import sys

from sqlalchemy import func, select

from app.core.config import settings
from app.db import SessionLocal
from app.models import User
from app.schemas.auth import UserCreate, UserUpdate
from app.services.ai_usage_report import ai_usage_report
from app.services.auth import create_user, serialize_user, update_user
from app.services.documents import build_object_storage
from app.services.graph_chat import PROMPT_VERSION
from app.services.graph_invariants import check_graph_invariants
from app.services.object_migration import (
    ObjectMigrationError,
    execute_object_migration,
    plan_object_migration,
    verify_object_migration,
)
from app.services.object_storage import DocumentError, LocalObjectStorage, RoutedObjectStorage
from app.services.providers.openai_graph_chat import graph_chat_provider


def _verify_chat_provider_access(provider_name: str) -> dict[str, object]:
    runtime = graph_chat_provider(provider_name)
    response = runtime.respond(
        input_items=[{"role": "user", "content": "Reply exactly OK."}],
        tools=[],
        instructions="Return only OK.",
        metadata={"operation": "operator-preflight", "prompt_version": PROMPT_VERSION},
    )
    return {
        "status": "ready",
        "provider": runtime.name,
        "model": runtime.model,
        "response_id_present": bool(response.response_id),
        "request_id_present": bool(response.request_id),
        "output_present": bool(response.text),
    }


def _password_from_stdin() -> str:
    if sys.stdin.isatty():
        return getpass.getpass("Mật khẩu: ")
    value = sys.stdin.readline().rstrip("\r\n")
    if not value:
        raise SystemExit("Cần cung cấp mật khẩu qua stdin")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Kiểm tra vận hành Hệ thống nghiên cứu")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-graph")
    subparsers.add_parser("verify-openai")
    provider_parser = subparsers.add_parser("verify-chat-provider")
    provider_parser.add_argument("--provider", choices=["openai", "deepseek"])
    create_parser = subparsers.add_parser("create-user")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--email", required=True)
    create_parser.add_argument("--role", choices=["owner", "researcher", "viewer"], required=True)
    create_parser.add_argument("--password-stdin", action="store_true", required=True)
    password_parser = subparsers.add_parser("set-password")
    password_parser.add_argument("--email", required=True)
    password_parser.add_argument("--password-stdin", action="store_true", required=True)
    usage_parser = subparsers.add_parser("ai-usage-report")
    usage_parser.add_argument("--since-hours", type=float, default=24.0)
    migration_parser = subparsers.add_parser("migrate-objects")
    migration_parser.add_argument("--mode", choices=["plan", "execute", "verify"], required=True)
    migration_parser.add_argument("--confirm-copy-only", action="store_true")
    args = parser.parse_args()
    if args.command == "ai-usage-report":
        with SessionLocal() as db:
            report = ai_usage_report(db, since_hours=args.since_hours)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.command == "verify-graph":
        with SessionLocal() as db:
            report = check_graph_invariants(db)
        print(json.dumps(report.model_dump(), indent=2))
        raise SystemExit(0 if report.valid else 1)
    if args.command == "verify-openai":
        provider_name = "openai"
    elif args.command == "verify-chat-provider":
        provider_name = args.provider or settings.graph_chat_default_provider
    else:
        provider_name = None
    if provider_name is not None:
        try:
            result = _verify_chat_provider_access(provider_name)
        except DocumentError as exc:
            model = (
                settings.openai_model
                if provider_name == "openai"
                else settings.deepseek_model
            )
            print(
                json.dumps(
                    {
                        "status": "unavailable",
                        "provider": provider_name,
                        "model": model,
                        "error_code": exc.code,
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            raise SystemExit(2) from exc
        print(json.dumps(result, sort_keys=True))
        return
    if args.command == "create-user":
        data = UserCreate(
            name=args.name,
            email=args.email,
            role=args.role,
            password=_password_from_stdin(),
        )
        with SessionLocal() as db:
            user = create_user(db, data, actor="operator-cli")
            output = serialize_user(user).model_dump(mode="json", exclude={"email"})
        print(json.dumps(output, indent=2))
        return
    if args.command == "set-password":
        email = args.email.strip().casefold()
        with SessionLocal() as db:
            user = db.scalar(select(User).where(func.lower(User.email) == email))
            if user is None:
                raise SystemExit("Không tìm thấy người dùng")
            user = update_user(
                db,
                user,
                UserUpdate(password=_password_from_stdin()),
                actor="operator-cli",
                actor_id="operator-cli",
            )
            output = serialize_user(user).model_dump(mode="json", exclude={"email"})
        print(json.dumps(output, indent=2))
        return
    if args.command == "migrate-objects":
        if args.mode == "execute" and not args.confirm_copy_only:
            raise SystemExit("Chế độ execute yêu cầu --confirm-copy-only")
        local = LocalObjectStorage(
            settings.document_storage_dir, settings.document_max_upload_bytes
        )
        try:
            with SessionLocal() as db:
                if args.mode == "plan":
                    result = asyncio.run(plan_object_migration(db, local)).report()
                else:
                    routed = build_object_storage()
                    if not isinstance(routed, RoutedObjectStorage) or routed.minio is None:
                        raise ObjectMigrationError(
                            "OBJECT_MIGRATION_NOT_CONFIGURED",
                            "Chế độ di chuyển này cần thông tin xác thực MinIO được quản lý.",
                        )
                    if args.mode == "execute":
                        result = asyncio.run(
                            execute_object_migration(db, local, routed.minio)
                        )
                    else:
                        result = asyncio.run(
                            verify_object_migration(db, local, routed.minio)
                        )
        except (DocumentError, ObjectMigrationError) as exc:
            print(
                json.dumps({"error": {"code": exc.code, "message": exc.message}}),
                file=sys.stderr,
            )
            raise SystemExit(2) from exc
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
