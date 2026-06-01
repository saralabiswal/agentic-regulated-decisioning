# Author: Sarala Biswal
"""Small Chrome DevTools UI smoke runner for local development."""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import time
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class CdpClient:
    """Minimal Chrome DevTools Protocol client used by the UI smoke test."""
    sock: socket.socket
    next_id: int = 1

    @classmethod
    def connect(cls, debugger_url: str) -> CdpClient:
        """Open a WebSocket connection to the first available Chrome debugger tab."""
        targets = json.loads(urlopen(f"{debugger_url}/json", timeout=5).read())
        target = next(
            item
            for item in targets
            if item.get("type") == "page" and item.get("url", "").startswith("http")
        )
        ws_url = target["webSocketDebuggerUrl"]
        _, address = ws_url.split("://", 1)
        host_port, path = address.split("/", 1)
        host, port = host_port.split(":", 1)
        sock = socket.create_connection((host, int(port)), timeout=5)
        sock.settimeout(20)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET /{path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode())
        response = b""
        while b"\r\n\r\n" not in response:
            response += sock.recv(4096)
        if b"101" not in response.splitlines()[0]:
            raise RuntimeError(response.decode(errors="replace"))
        return cls(sock=sock)

    def command(self, method: str, params: dict | None = None) -> dict:
        """Send a DevTools command and return the matching response payload."""
        message_id = self.next_id
        self.next_id += 1
        self._send_json({"id": message_id, "method": method, "params": params or {}})
        deadline = time.time() + 15
        while time.time() < deadline:
            payload = self._recv_json()
            if payload.get("id") == message_id:
                if "error" in payload:
                    raise RuntimeError(payload["error"])
                return payload["result"]
        raise TimeoutError(method)

    def evaluate(self, expression: str) -> str:
        """Evaluate JavaScript in the browser and return the serialized result."""
        result = self.command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        value = result["result"].get("value")
        return "" if value is None else str(value)

    def _send_json(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) <= 65535:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", len(data)))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", len(data)))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
        self.sock.sendall(header + masked)

    def _recv_json(self) -> dict:
        first, second = self._read_exact(2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        masked = bool(second & 0x80)
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 8:
            raise RuntimeError("Chrome closed the DevTools websocket")
        return json.loads(payload.decode())

    def _read_exact(self, length: int) -> bytes:
        data = b""
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise RuntimeError("socket closed")
            data += chunk
        return data


def click_text(label: str, wait_ms: int = 800) -> str:
    """Generate JavaScript that clicks the first visible button with matching text."""
    return f"""
    new Promise((resolve) => {{
      const element = [...document.querySelectorAll('button,a')]
        .find((item) => item.textContent.includes({json.dumps(label)}));
      if (!element) {{
        resolve('missing:{label}');
        return;
      }}
      element.click();
      setTimeout(() => resolve(document.body.innerText), {wait_ms});
    }})
    """


def set_select_value(selector: str, value: str, wait_ms: int = 800) -> str:
    """Generate JavaScript that updates a select element and dispatches change events."""
    return f"""
    new Promise((resolve) => {{
      const element = document.querySelector({json.dumps(selector)});
      if (!element) {{
        resolve('missing:{selector}');
        return;
      }}
      element.value = {json.dumps(value)};
      element.dispatchEvent(new Event('change', {{ bubbles: true }}));
      setTimeout(() => resolve(document.body.innerText), {wait_ms});
    }})
    """


def main() -> None:
    """Run this module as a command-line entry point."""
    client = CdpClient.connect("http://127.0.0.1:9222")
    client.command("Runtime.enable")
    client.command("Page.enable")
    client.command("Page.navigate", {"url": "http://127.0.0.1:5173/"})
    time.sleep(1.5)
    client.evaluate("localStorage.clear(); location.reload();")
    time.sleep(1.5)
    print(
        "initial",
        "Insurance Decision Cockpit" in client.evaluate("document.body.innerText"),
    )
    print("studio", "Playbook Builder" in client.evaluate(click_text("Playbook Studio")))
    print(
        "template_count",
        int(client.evaluate("document.querySelectorAll('.template-list button').length")) >= 5,
    )
    print(
        "domain_switch",
        "Lending decision asset" in client.evaluate(set_select_value("select", "lending")),
    )
    print(
        "domain_template_count",
        int(client.evaluate("document.querySelectorAll('.template-list button').length")) >= 5,
    )
    print(
        "domain_back",
        "Insurance decision asset" in client.evaluate(set_select_value("select", "insurance")),
    )
    print(
        "template_select",
        "ready to validate"
        in client.evaluate(
            """
            new Promise((resolve) => {
              const element = document.querySelector('.template-list button');
              if (!element) {
                resolve('missing:template');
                return;
              }
              element.click();
              setTimeout(() => resolve(document.body.innerText.toLowerCase()), 1200);
            })
            """
        ),
    )
    print("validate", "ready to run" in client.evaluate(click_text("Validate", 1500)).lower())
    print(
        "run",
        "decision package is ready"
        in client.evaluate(click_text("Run Playbook and open outcome", 8000)).lower(),
    )
    print(
        "download_prompt",
        "downloaded" in client.evaluate(click_text("Download decision report", 1500)).lower(),
    )
    print("queue", "Human review workbench" in client.evaluate(click_text("Referral Queue")))
    print(
        "review_action",
        "decision recorded" in client.evaluate(click_text("Confirm recommendation", 1500)).lower(),
    )
    print(
        "audit",
        "audit timeline" in client.evaluate(click_text("Audit & Reports")).lower(),
    )
    print(
        "architecture",
        "architecture walkthrough" in client.evaluate(click_text("Architecture")).lower(),
    )
    print(
        "architecture_story_picture",
        "complete story" in client.evaluate("document.body.innerText").lower(),
    )
    print(
        "architecture_next",
        "async event stream" in client.evaluate(click_text("Next layer", 1000)).lower(),
    )
    print(
        "settings",
        "runtime control center" in client.evaluate(click_text("Settings")).lower(),
    )
    client.evaluate(set_select_value(".settings-control select", "mock", 400))
    print(
        "settings_mock",
        "runtime settings applied"
        in client.evaluate(click_text("Apply mock-only runtime", 1200)).lower(),
    )
    print(
        "settings_mock_defaults",
        client.evaluate(
            """
            (() => {
              const controls = [...document.querySelectorAll('.settings-control select,input')];
              return controls.map((item) => item.value).join('|');
            })()
            """
        )
        == "mock|mock|mock",
    )
    print(
        "settings_service_links",
        int(
            client.evaluate(
                "document.querySelectorAll('.settings-service-list a.service-row').length"
            )
        )
        >= 1,
    )
    print(
        "settings_stream_inspector",
        "stream inspector" in client.evaluate("document.body.innerText").lower(),
    )
    client.evaluate(click_text("Technical", 100))
    print("operations", "Technical platform map" in client.evaluate(click_text("Operations")))


if __name__ == "__main__":
    main()
