"""Offline tests forbid external connections and remove provider credentials."""

import socket
import pytest


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    for name in (
        "OPENAI_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_TRACING_V2",
    ):
        monkeypatch.delenv(name, raising=False)
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def local_control_channel(sock, address):
        return (
            sock.family == getattr(socket, "AF_UNIX", None)
            or isinstance(address, tuple)
            and address[0] in {"127.0.0.1", "::1", "localhost"}
        )

    def blocked_connect(sock, address):
        if local_control_channel(sock, address):
            return original_connect(sock, address)
        raise AssertionError("External network access is forbidden in offline tests")

    def blocked_connect_ex(sock, address):
        if local_control_channel(sock, address):
            return original_connect_ex(sock, address)
        raise AssertionError("External network access is forbidden in offline tests")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked_connect_ex)
