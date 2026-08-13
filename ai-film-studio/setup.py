#!/usr/bin/env python3
"""
setup.py — one-command setup for AI Film Studio.

Creates a virtualenv, installs Python dependencies, prepares config files,
sets up MoneyPrinterTurbo (optional), and verifies ffmpeg.

Usage:
    python3 setup.py            # full setup
    python3 setup.py --no-mpt   # skip MoneyPrinterTurbo dependency sync

After setup, run:
    ./run.sh --idea "..."        (Linux/macOS)
    run.bat --idea "..."         (Windows)
    # or directly:
    .venv/bin/python run_film.py --idea "..."      (Linux/macOS)
    .venv\Scripts\python run_film.py --idea "..."  (Windows)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
CONFIG = ROOT / "config.toml"
CONFIG_EXAMPLE = ROOT / "config.example.toml"
MPT_DIR = ROOT.parent / "repos" / "MoneyPrinterTurbo"
MPT_CONFIG_TEMPLATE = ROOT / "templates" / "moneyprinterturbo.config.toml"
MPT_CONFIG = MPT_DIR / "config.toml"


def sh(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    print("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None)


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def step(title: str) -> None:
    print(f"\n\033[1;36m==> {title}\033[0m")


def ok(msg: str) -> None:
    print(f"   \033[32m✓ {msg}\033[0m")


def warn(msg: str) -> None:
    print(f"   \033[33m! {msg}\033[0m")


def check_python() -> None:
    step("Checking Python")
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11+ required (found {})".format(sys.version.split()[0]))
        sys.exit(2)
    ok(f"Python {sys.version.split()[0]}")


def create_venv() -> None:
    step("Creating virtualenv (.venv)")
    if venv_python().exists():
        ok(".venv already exists")
        return
    import venv

    venv.EnvBuilder(with_pip=True).create(str(VENV))
    ok(".venv created")


def install_deps() -> None:
    step("Installing Python dependencies (google-genai, edge-tts, ...)")
    py = venv_python()
    sh([py, "-m", "pip", "install", "--upgrade", "pip"])
    r = sh([py, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    if r.returncode != 0:
        print("ERROR: dependency install failed")
        sys.exit(2)
    ok("dependencies installed")


def verify_imports() -> None:
    step("Verifying imports")
    py = venv_python()
    for mod in ("google.genai", "edge_tts", "imageio_ffmpeg",
                "googleapiclient", "google_auth_oauthlib"):
        r = subprocess.run(
            [str(py), "-c", f"import {mod}"], capture_output=True, text=True
        )
        if r.returncode == 0:
            ok(mod)
        else:
            warn(f"{mod} failed to import: {r.stderr.strip()[:200]}")


def prepare_config() -> None:
    step("Preparing ai-film-studio/config.toml")
    if CONFIG.exists():
        ok("config.toml already present (skipped)")
    else:
        shutil.copyfile(CONFIG_EXAMPLE, CONFIG)
        ok("config.toml created from example")
    # check key
    try:
        if sys.version_info >= (3, 11):
            import tomllib

            with CONFIG.open("rb") as fh:
                cfg = tomllib.load(fh)
        else:
            cfg = {}
        if not cfg.get("gemini_api_key"):
            warn("gemini_api_key is EMPTY — fill it before running "
                 "(https://aistudio.google.com/app/apikey)")
    except Exception:
        pass


def check_ffmpeg() -> None:
    step("Checking ffmpeg")
    exe = shutil.which("ffmpeg")
    if exe:
        ok(f"system ffmpeg: {exe}")
        return
    py = venv_python()
    r = subprocess.run(
        [str(py), "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
        capture_output=True, text=True,
    )
    if r.returncode == 0 and r.stdout.strip():
        ok(f"using imageio-ffmpeg: {r.stdout.strip()}")
    else:
        warn("ffmpeg not found; imageio-ffmpeg will be used (auto-download on first use)")


def setup_mpt() -> None:
    step("Setting up MoneyPrinterTurbo")
    if not MPT_DIR.exists():
        warn(f"{MPT_DIR} not found (skipped)")
        return

    # config
    if MPT_CONFIG.exists():
        ok("MPT config.toml already present")
    elif MPT_CONFIG_TEMPLATE.exists():
        shutil.copyfile(MPT_CONFIG_TEMPLATE, MPT_CONFIG)
        ok("MPT config.toml created from template (Gemini + Hindi font)")
    else:
        warn("MPT config template missing")

    # deps via uv (fast) if uv exists and .venv missing
    mpt_venv = MPT_DIR / ".venv"
    if mpt_venv.exists():
        ok("MPT .venv already synced")
        return
    uv = shutil.which("uv")
    if uv:
        r = sh([uv, "sync", "--frozen"], cwd=MPT_DIR)
        if r.returncode == 0:
            ok("MPT deps synced via uv")
        else:
            warn("uv sync failed; run manually: cd repos/MoneyPrinterTurbo && uv sync")
    else:
        warn("uv not found — install it (pip install uv) then run: "
             "cd repos/MoneyPrinterTurbo && uv sync --frozen")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--no-mpt", action="store_true", help="skip MoneyPrinterTurbo setup")
    args = p.parse_args()

    print("=" * 64)
    print("  AI Film Studio — Setup")
    print("=" * 64)

    check_python()
    create_venv()
    install_deps()
    verify_imports()
    prepare_config()
    check_ffmpeg()
    if not args.no_mpt:
        setup_mpt()

    step("Setup complete")
    print("""
Next steps:
  1) Gemini API key daalo (dono files mein):
       ai-film-studio/config.toml          -> gemini_api_key = "..."
       repos/MoneyPrinterTurbo/config.toml -> gemini_api_key = "..."
     (Veo 3.1 video ke liye is key par paid Cloud billing chahiye)

  2) Run:
       ./run.sh --idea "आपकी कहानी" --engine mpt     (faceless, ₹0)
       ./run.sh --idea "आपकी कहानी"                 (Veo cinematic)

  3) YouTube upload (optional): client_secrets.json banakar
       ai-film-studio/ mein rakho (README section 5 dekho)
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
