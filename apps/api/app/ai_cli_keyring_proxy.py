"""Private Secret Service exposing only the Antigravity CLI credential.

dbus/gi are loaded only by the host executable, never by the application server.
Secrets stay in the host keyring; this service validates every object/session and
write before forwarding. It never logs attributes, values or upstream errors.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = "/org/freedesktop/secrets"
SERVICE = "org.freedesktop.Secret.Service"
ITEM = "org.freedesktop.Secret.Item"
COLLECTION = "org.freedesktop.Secret.Collection"
SESSION = "org.freedesktop.Secret.Session"
PROPERTIES = "org.freedesktop.DBus.Properties"
SCOPE = {"service": "gemini", "username": "antigravity"}
SCHEMA = "org.freedesktop.Secret.Generic"


class KeyringDenied(Exception):
    pass


@dataclass
class KeyringPolicy:
    items: set[str]
    sessions: set[str] = field(default_factory=set)

    @property
    def collections(self) -> set[str]:
        return {item.rsplit("/", 1)[0] for item in self.items}

    def require_items(self, paths: Any) -> None:
        if not set(map(str, paths)).issubset(self.items):
            raise KeyringDenied("Credential outside application scope")

    def require_session(self, session: Any) -> None:
        if str(session) not in self.sessions:
            raise KeyringDenied("Unknown credential session")

    def require_attributes(self, attributes: Any) -> None:
        attrs = dict(attributes)
        if any(str(attrs.get(key, "")) != value for key, value in SCOPE.items()):
            raise KeyringDenied("Credential outside application scope")
        if set(attrs) - (set(SCOPE) | {"xdg:schema"}):
            raise KeyringDenied("Unexpected credential attributes")
        if "xdg:schema" in attrs and str(attrs["xdg:schema"]) != SCHEMA:
            raise KeyringDenied("Unexpected credential schema")


def serve(socket: Path) -> None:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    os.umask(0o077)
    DBusGMainLoop(set_as_default=True)
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS") or f"unix:path=/run/user/{os.getuid()}/bus"
    host = dbus.bus.BusConnection(address)

    def remote(path: str, interface: str, method: str, *args: Any, signature: str) -> Any:
        obj = host.get_object("org.freedesktop.secrets", path, introspect=False)
        return obj.get_dbus_method(method, interface)(*args, signature=signature, timeout=15)

    unlocked, locked = remote(ROOT, SERVICE, "SearchItems", SCOPE, signature="a{ss}")
    if locked or not unlocked:
        raise KeyringDenied("Application credential unavailable or locked")
    policy = KeyringPolicy(set(map(str, unlocked)))
    for path in policy.items:
        attrs = remote(path, PROPERTIES, "Get", ITEM, "Attributes", signature="ss")
        policy.require_attributes(attrs)

    daemon = subprocess.Popen(
        [
            "/usr/bin/dbus-daemon",
            "--session",
            "--nofork",
            "--nopidfile",
            f"--address=unix:path={socket}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    objects: dict[str, Any] = {}
    ready = socket.with_suffix(".ready")
    try:
        deadline = time.monotonic() + 5
        while not socket.exists():
            if daemon.poll() is not None or time.monotonic() > deadline:
                raise KeyringDenied("Private bus unavailable")
            time.sleep(0.02)
        local = dbus.bus.BusConnection(f"unix:path={socket}")
        owner = dbus.service.BusName("org.freedesktop.secrets", local, do_not_queue=True)

        def require(check: Any, *args: Any) -> None:
            try:
                check(*args)
            except KeyringDenied:
                raise dbus.exceptions.DBusException(
                    "Credential access denied", name="org.freedesktop.DBus.Error.AccessDenied"
                ) from None

        def check_secret(secret: Any) -> None:
            require(policy.require_session, secret[0])

        class PathObject(dbus.service.Object):
            @property
            def object_path(self) -> str:
                return str(self.__dbus_object_path__)

        class PropertiesObject(PathObject):
            def properties(self, interface: str) -> dict[str, Any]:
                return {}

            @dbus.service.method(PROPERTIES, in_signature="ss", out_signature="v")
            def Get(self, interface: str, name: str) -> Any:
                values = self.properties(interface)
                if name not in values:
                    raise dbus.exceptions.DBusException(
                        "Unknown property", name="org.freedesktop.DBus.Error.InvalidArgs"
                    )
                return values[name]

            @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
            def GetAll(self, interface: str) -> dict[str, Any]:
                return self.properties(interface)

            @dbus.service.method(PROPERTIES, in_signature="ssv", out_signature="")
            def Set(self, _interface: str, _name: str, _value: Any) -> None:
                raise dbus.exceptions.DBusException(
                    "Property writes denied", name="org.freedesktop.DBus.Error.AccessDenied"
                )

        class SessionObject(PathObject):
            @dbus.service.method(SESSION, in_signature="", out_signature="")
            def Close(self) -> None:
                require(policy.require_session, self.object_path)
                remote(self.object_path, SESSION, "Close", signature="")
                policy.sessions.discard(str(self.object_path))

        class ItemObject(PropertiesObject):
            def properties(self, interface: str) -> dict[str, Any]:
                if interface != ITEM:
                    return {}
                require(policy.require_items, [self.object_path])
                attrs = remote(
                    self.object_path, PROPERTIES, "Get", ITEM, "Attributes", signature="ss"
                )
                require(policy.require_attributes, attrs)
                return {
                    "Attributes": dbus.Dictionary(attrs, signature="ss"),
                    "Label": dbus.String("Antigravity CLI credential"),
                    "Locked": dbus.Boolean(False),
                    "Created": dbus.UInt64(0),
                    "Modified": dbus.UInt64(0),
                }

            @dbus.service.method(ITEM, in_signature="o", out_signature="(oayays)")
            def GetSecret(self, session: Any) -> Any:
                require(policy.require_items, [self.object_path])
                require(policy.require_session, session)
                return remote(self.object_path, ITEM, "GetSecret", session, signature="o")

            @dbus.service.method(ITEM, in_signature="(oayays)", out_signature="")
            def SetSecret(self, secret: Any) -> None:
                require(policy.require_items, [self.object_path])
                check_secret(secret)
                remote(self.object_path, ITEM, "SetSecret", secret, signature="(oayays)")

        def register_item(path: str) -> None:
            if path not in objects:
                objects[path] = ItemObject(owner, path)

        class CollectionObject(PropertiesObject):
            def properties(self, interface: str) -> dict[str, Any]:
                if interface != COLLECTION:
                    return {}
                return {
                    "Items": dbus.Array(
                        [
                            dbus.ObjectPath(p)
                            for p in policy.items
                            if p.rsplit("/", 1)[0] == self.object_path
                        ],
                        signature="o",
                    ),
                    "Label": dbus.String("Login"),
                    "Locked": dbus.Boolean(False),
                    "Created": dbus.UInt64(0),
                    "Modified": dbus.UInt64(0),
                }

            @dbus.service.method(COLLECTION, in_signature="a{ss}", out_signature="ao")
            def SearchItems(self, attributes: Any) -> Any:
                found, _ = remote(ROOT, SERVICE, "SearchItems", attributes, signature="a{ss}")
                return [
                    p
                    for p in found
                    if str(p) in policy.items and str(p).rsplit("/", 1)[0] == self.object_path
                ]

            @dbus.service.method(COLLECTION, in_signature="a{sv}(oayays)b", out_signature="oo")
            def CreateItem(self, properties: Any, secret: Any, replace: bool) -> Any:
                require(policy.require_attributes, properties.get(f"{ITEM}.Attributes", {}))
                check_secret(secret)
                if not replace or set(properties) - {f"{ITEM}.Attributes", f"{ITEM}.Label"}:
                    raise dbus.exceptions.DBusException(
                        "Credential creation denied", name="org.freedesktop.DBus.Error.AccessDenied"
                    )
                path, prompt = remote(
                    self.object_path,
                    COLLECTION,
                    "CreateItem",
                    properties,
                    secret,
                    True,
                    signature="a{sv}(oayays)b",
                )
                if str(prompt) != "/" or str(path).rsplit("/", 1)[0] != self.object_path:
                    raise KeyringDenied("Credential replacement unavailable")
                policy.items.add(str(path))
                register_item(str(path))
                return path, dbus.ObjectPath("/")

        class ServiceObject(PropertiesObject):
            def properties(self, interface: str) -> dict[str, Any]:
                if interface != SERVICE:
                    return {}
                return {"Collections": dbus.Array(sorted(policy.collections), signature="o")}

            @dbus.service.method(SERVICE, in_signature="sv", out_signature="vo")
            def OpenSession(self, algorithm: str, value: Any) -> Any:
                result, path = remote(
                    ROOT, SERVICE, "OpenSession", algorithm, value, signature="sv"
                )
                policy.sessions.add(str(path))
                objects[str(path)] = SessionObject(owner, path)
                return result, path

            @dbus.service.method(SERVICE, in_signature="a{ss}", out_signature="aoao")
            def SearchItems(self, attributes: Any) -> Any:
                found, _ = remote(ROOT, SERVICE, "SearchItems", attributes, signature="a{ss}")
                return [p for p in found if str(p) in policy.items], dbus.Array([], signature="o")

            @dbus.service.method(SERVICE, in_signature="aoo", out_signature="a{o(oayays)}")
            def GetSecrets(self, items: Any, session: Any) -> Any:
                require(policy.require_items, items)
                require(policy.require_session, session)
                result = remote(ROOT, SERVICE, "GetSecrets", items, session, signature="aoo")
                require(policy.require_items, result.keys())
                return result

            @dbus.service.method(SERVICE, in_signature="ao", out_signature="aoo")
            def Unlock(self, paths: Any) -> Any:
                # Expose already-unlocked scoped objects; never unlock a host collection.
                if not set(map(str, paths)).issubset(policy.items | policy.collections):
                    raise dbus.exceptions.DBusException(
                        "Unlock denied", name="org.freedesktop.DBus.Error.AccessDenied"
                    )
                return paths, dbus.ObjectPath("/")

            @dbus.service.method(SERVICE, in_signature="s", out_signature="o")
            def ReadAlias(self, alias: str) -> Any:
                return dbus.ObjectPath(sorted(policy.collections)[0] if alias == "default" else "/")

        objects[ROOT] = ServiceObject(owner, ROOT)
        for path in policy.collections:
            objects[path] = CollectionObject(owner, path)
        for path in policy.items:
            register_item(path)
        loop = GLib.MainLoop()
        signal.signal(signal.SIGTERM, lambda *_args: loop.quit())
        signal.signal(signal.SIGINT, lambda *_args: loop.quit())
        ready.touch(mode=0o600)
        loop.run()
    finally:
        ready.unlink(missing_ok=True)
        daemon.terminate()
        try:
            daemon.wait(timeout=2)
        except subprocess.TimeoutExpired:
            daemon.kill()
            daemon.wait()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True, type=Path)
    args = parser.parse_args()
    try:
        serve(args.socket)
    except Exception:
        print("KEYRING_PROXY_UNAVAILABLE", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
