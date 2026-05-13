import shutil
import subprocess
import sys
from pathlib import Path

import typer

from zana.tui.theme import console

PACKAGE_NAME = "vecanova-zana"

DATA_DIRS: list[Path] = [
    Path.home() / ".zana",
    Path.home() / ".local" / "share" / "com.vecanova.zana",
]


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def _find_pipx() -> str | None:
    return shutil.which("pipx")


def _find_uv() -> str | None:
    uv = shutil.which("uv")
    if uv:
        return uv
    uv_home = Path.home() / ".local" / "bin" / "uv"
    return str(uv_home) if uv_home.exists() else None


def _remove_package() -> bool:
    pipx = _find_pipx()
    if pipx:
        result = subprocess.run([pipx, "uninstall", PACKAGE_NAME], capture_output=True)
        if result.returncode == 0:
            return True
        # Try the short name in case it was installed as just "zana"
        result2 = subprocess.run([pipx, "uninstall", "zana"], capture_output=True)
        return result2.returncode == 0

    uv = _find_uv()
    if uv:
        result = subprocess.run(
            [uv, "tool", "uninstall", PACKAGE_NAME], capture_output=True
        )
        if result.returncode == 0:
            return True
        result2 = subprocess.run([uv, "tool", "uninstall", "zana"], capture_output=True)
        return result2.returncode == 0

    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", PACKAGE_NAME, "-y"],
        capture_output=True,
    )
    return result.returncode == 0


def _remove_data_dirs() -> list[Path]:
    removed = []
    for d in DATA_DIRS:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d)
    return removed


def cmd_uninstall(purge: bool = False, yes: bool = False) -> None:
    console.print("\n[primary]ZANA — Protocolo de Desinstalación[/primary]")
    console.print("[muted]─────────────────────────────────────[/muted]\n")

    existing_data = [d for d in DATA_DIRS if d.exists()]

    if purge:
        console.print(
            "[warning]Modo:[/warning] [error]COMPLETO[/error] — paquete + todos los datos"
        )
        if existing_data:
            console.print("\n[muted]Directorios de datos que serán eliminados:[/muted]")
            for d in existing_data:
                try:
                    size = _dir_size_mb(d)
                    console.print(
                        f"  [accent]•[/accent] {d}  [muted]({size:.1f} MB)[/muted]"
                    )
                except Exception:
                    console.print(f"  [accent]•[/accent] {d}")
        else:
            console.print("[muted]No se encontraron directorios de datos.[/muted]")
    else:
        console.print(
            "[warning]Modo:[/warning] [accent]PARCIAL[/accent] — solo el paquete CLI"
        )
        if existing_data:
            console.print("\n[muted]Datos conservados (no se tocarán):[/muted]")
            for d in existing_data:
                console.print(f"  [success]✓[/success] {d}")
        console.print(
            "\n[muted]Tip: usa [accent]zana uninstall --purge[/accent] para eliminar también los datos.[/muted]"
        )

    console.print()

    if not yes:
        if purge:
            confirm_phrase = "eliminar zana"
            console.print(
                f"[warning]⚠  Esta acción es irreversible.[/warning]\n"
                f"   Escribe [accent]{confirm_phrase}[/accent] para confirmar:"
            )
            typed = typer.prompt("  >", default="")
            if typed.strip().lower() != confirm_phrase:
                console.print(
                    f"\n[error]Texto incorrecto.[/error] "
                    f"[muted]Se esperaba: «{confirm_phrase}»[/muted]"
                )
                console.print("[muted]Desinstalación cancelada.[/muted]")
                raise typer.Exit(1)
        else:
            confirmed = typer.confirm(
                "  ¿Confirmas eliminar el paquete CLI?", default=False
            )
            if not confirmed:
                console.print("\n[muted]Desinstalación cancelada.[/muted]")
                raise typer.Exit(0)

    console.print()

    # Step 1: remove the package
    console.print("[muted]Eliminando paquete...[/muted]")
    if _remove_package():
        console.print("[success]✅ Paquete eliminado.[/success]")
    else:
        console.print("[error]No se pudo eliminar el paquete automáticamente.[/error]")
        console.print("[yellow]Elimínalo manualmente:[/yellow]")
        console.print(f"  [accent]pipx uninstall {PACKAGE_NAME}[/accent]")
        console.print(f"  [accent]pip uninstall {PACKAGE_NAME} -y[/accent]")
        raise typer.Exit(1)

    # Step 2 (purge only): remove data dirs
    if purge:
        console.print("[muted]Eliminando datos...[/muted]")
        removed = _remove_data_dirs()
        if removed:
            for d in removed:
                console.print(f"  [success]✅[/success] {d} eliminado")
        else:
            console.print("[muted]No había datos que eliminar.[/muted]")

    console.print()
    console.print("[primary]ZANA desinstalado.[/primary]")
    if not purge and existing_data:
        console.print(
            "[muted]Tus datos permanecen en caso de reinstalación futura.[/muted]"
        )
    console.print("[muted]Hasta la próxima batalla, guerrero.[/muted]")
