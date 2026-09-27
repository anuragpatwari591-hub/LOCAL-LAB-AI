"""Launcher script tests: existence, executable bits, and shell syntax.

Actual execution of .bat/.ps1 is not possible on this Linux CI runner, so
those are checked for existence/consistency only; .sh scripts are checked
for real syntax validity via `bash -n`.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

COMMANDS = ["start", "prepare", "diagnose", "offline-check", "deploy-usb"]


@pytest.mark.parametrize("command", COMMANDS)
def test_all_three_platform_variants_exist(command):
    assert (REPO_ROOT / f"{command}.sh").exists(), f"{command}.sh missing"
    assert (REPO_ROOT / f"{command}.bat").exists(), f"{command}.bat missing"
    assert (REPO_ROOT / f"{command}.ps1").exists(), f"{command}.ps1 missing"


@pytest.mark.parametrize("command", COMMANDS)
def test_sh_scripts_are_executable(command):
    path = REPO_ROOT / f"{command}.sh"
    assert path.stat().st_mode & 0o111, f"{command}.sh is not executable"


@pytest.mark.parametrize("command", COMMANDS)
def test_sh_scripts_have_valid_bash_syntax(command):
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    path = REPO_ROOT / f"{command}.sh"
    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("command", COMMANDS)
def test_sh_scripts_resolve_project_root_from_own_location(command):
    text = (REPO_ROOT / f"{command}.sh").read_text()
    assert "LOCAL_LAB_AI_ROOT" in text
    assert "BASH_SOURCE" in text
    # Never hardcode a Windows drive letter or a fixed dev path.
    assert "C:\\" not in text
    assert "/home/" not in text


@pytest.mark.parametrize("command", COMMANDS)
def test_bat_scripts_resolve_project_root_from_own_location(command):
    text = (REPO_ROOT / f"{command}.bat").read_text()
    assert "%~dp0" in text
    assert "LOCAL_LAB_AI_ROOT" in text


@pytest.mark.parametrize("command", COMMANDS)
def test_ps1_scripts_resolve_project_root_from_own_location(command):
    text = (REPO_ROOT / f"{command}.ps1").read_text()
    assert "$MyInvocation.MyCommand.Path" in text
    assert "LOCAL_LAB_AI_ROOT" in text
