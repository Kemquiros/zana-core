import socket
import time
from dataclasses import dataclass
from typing import Literal

import httpx
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

from cli.tui.theme import console

# (name, probe_type, host_or_url, port_or_None, description)
SERVICES: list[tuple[str, Literal["http", "tcp"], str, int | None, str]] = [
    ("Gateway", "http", "http://localhost:54446/health", None, "Sensory + Armor"),
    (
        "ChromaDB",
        "http",
        "http://localhost:58001/api/v1/heartbeat",
        None,
        "Semantic Memory",
    ),
    ("PostgreSQL", "tcp", "localhost", 55433, "Episodic Memory"),
    ("Redis", "tcp", "localhost", 56380, "Session Cache"),
    ("Neo4j", "http", "http://localhost:57474", None, "World Model"),
    ("ARIA UI", "http", "http://localhost:54448", None, "PWA Interface"),
]


@dataclass
class ServiceStatus:
    name: str
    description: str
    online: bool
    latency_ms: float | None


def _probe_http(url: str) -> tuple[bool, float | None]:
    try:
        t0 = time.perf_counter()
        r = httpx.get(url, timeout=2)
        latency = (time.perf_counter() - t0) * 1000
        return r.status_code < 500, round(latency, 1)
    except Exception:
        return False, None


def _probe_tcp(host: str, port: int) -> tuple[bool, float | None]:
    try:
        t0 = time.perf_counter()
        with socket.create_connection((host, port), timeout=2):
            latency = (time.perf_counter() - t0) * 1000
        return True, round(latency, 1)
    except Exception:
        return False, None


def _probe(probe_type: str, target: str, port: int | None) -> tuple[bool, float | None]:
    if probe_type == "tcp" and port is not None:
        return _probe_tcp(target, port)
    return _probe_http(target)


def _build_table(statuses: list[ServiceStatus], zfi: int) -> Panel:
    table = Table(show_header=True, header_style="header", box=None, padding=(0, 1))
    table.add_column("Component", style="bold white", width=14)
    table.add_column("Status", width=10)
    table.add_column("Latency", width=10)
    table.add_column("Role", style="muted")

    for s in statuses:
        status_cell = (
            "[success]✓ Online[/success]" if s.online else "[error]✗ Offline[/error]"
        )
        latency_cell = f"{s.latency_ms}ms" if s.latency_ms else "—"
        table.add_row(s.name, status_cell, latency_cell, s.description)

    online_count = sum(1 for s in statuses if s.online)
    zfi_color = "success" if zfi >= 90 else "warning" if zfi >= 60 else "error"
    zfi_label = f"[{zfi_color}]ZFI {zfi}/100[/{zfi_color}]"
    footer = f"  {online_count}/{len(statuses)} services online  ·  {zfi_label}"

    return Panel(
        table,
        title="[header] ZANA STATUS [/header]",
        subtitle=footer,
        border_style="magenta",
        padding=(0, 1),
    )


def _compute_zfi(statuses: list[ServiceStatus]) -> int:
    weights = {
        "Gateway": 30,
        "ChromaDB": 20,
        "PostgreSQL": 15,
        "Redis": 10,
        "Neo4j": 15,
        "ARIA UI": 10,
    }
    score = sum(weights.get(s.name, 0) for s in statuses if s.online)
    return score


def cmd_status(watch: bool = False) -> None:
    def _refresh() -> Panel:
        statuses = []
        for name, probe_type, target, port, desc in SERVICES:
            online, latency = _probe(probe_type, target, port)
            statuses.append(ServiceStatus(name, desc, online, latency))
        zfi = _compute_zfi(statuses)
        return _build_table(statuses, zfi)

    if watch:
        with Live(_refresh(), refresh_per_second=0.5, console=console) as live:
            try:
                while True:
                    time.sleep(5)
                    live.update(_refresh())
            except KeyboardInterrupt:
                pass
    else:
        console.print(_refresh())
