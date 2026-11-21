"""Run `{{name}} serve` on a free port and call it like the plugin (header) and claude.ai (key in URL) do."""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import anyio
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

EXE = os.path.join(os.path.dirname(sys.executable), "{{name}}")
KEY = "{{pkg}}_testkey123"


@pytest.fixture(scope="module")
def base():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "{{PKG}}_API_KEYS": KEY, "{{PKG}}_PORT": str(port)}
    proc = subprocess.Popen([EXE, "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "/healthz", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def _hello(transport_or_url):
    async def go():
        async with Client(transport_or_url) as c:
            return (await c.call_tool("hello", {"name": "Lucas"})).content[0].text

    return anyio.run(go)


def test_rejects_missing_key(base):
    req = urllib.request.Request(base + "/mcp", data=b"{}", headers={"content-type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 401


def test_key_in_header(base):
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {KEY}"})
    assert _hello(streamable_http_client(base + "/mcp", http_client=http)) == "Hello, Lucas!"


def test_key_in_url(base):
    assert _hello(f"{base}/mcp/{KEY}") == "Hello, Lucas!"
