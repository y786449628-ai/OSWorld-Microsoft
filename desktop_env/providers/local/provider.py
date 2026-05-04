import logging
import os
import shlex
import subprocess
import time
from typing import Optional

import requests

from desktop_env.providers.base import Provider

logger = logging.getLogger("desktopenv.providers.local.LocalProvider")
logger.setLevel(logging.INFO)

WAIT_TIME = 2


class LocalProvider(Provider):
    def __init__(self, region: str = None):
        super().__init__(region)
        self.server_host = os.getenv("OSWORLD_LOCAL_HOST", "127.0.0.1")
        self.server_port = int(os.getenv("OSWORLD_LOCAL_SERVER_PORT", "5000"))
        self.chromium_port = int(os.getenv("OSWORLD_LOCAL_CHROMIUM_PORT", "9222"))
        self.vnc_port = int(os.getenv("OSWORLD_LOCAL_VNC_PORT", "8006"))
        self.vlc_port = int(os.getenv("OSWORLD_LOCAL_VLC_PORT", "8080"))
        self.reset_command = os.getenv(
            "OSWORLD_LOCAL_RESET_COMMAND",
            "powershell -ExecutionPolicy Bypass -File deploy\\wuying\\reset_workspace.ps1",
        )
        self.start_command = os.getenv("OSWORLD_LOCAL_START_COMMAND", "")
        self.stop_command = os.getenv("OSWORLD_LOCAL_STOP_COMMAND", "")

    @property
    def server_root(self) -> str:
        return f"http://{self.server_host}:{self.server_port}"

    def _wait_for_server(self, timeout: int = 60) -> None:
        started_at = time.time()
        while time.time() - started_at < timeout:
            for endpoint in ("/screenshot", "/terminal"):
                try:
                    response = requests.get(f"{self.server_root}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        return
                except requests.RequestException:
                    pass
            time.sleep(WAIT_TIME)
        raise TimeoutError(f"Local desktop server not ready at {self.server_root}")

    def _run_shell_command(self, command: Optional[str], label: str) -> None:
        if not command:
            return
        logger.info("%s: %s", label, command)
        result = subprocess.run(
            shlex.split(command, posix=False),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{label} failed with exit code {result.returncode}: {result.stderr or result.stdout}"
            )

    def start_emulator(self, path_to_vm: str, headless: bool, os_type: str):
        if self.start_command:
            self._run_shell_command(self.start_command, "local start command")
        self._wait_for_server()

    def get_ip_address(self, path_to_vm: str) -> str:
        return (
            f"{self.server_host}:{self.server_port}:"
            f"{self.chromium_port}:{self.vnc_port}:{self.vlc_port}"
        )

    def save_state(self, path_to_vm: str, snapshot_name: str):
        logger.info("Local provider does not support VM snapshots. Skipping save_state.")

    def revert_to_snapshot(self, path_to_vm: str, snapshot_name: str) -> str:
        self._run_shell_command(self.reset_command, "local reset command")
        self._wait_for_server()
        return path_to_vm

    def stop_emulator(self, path_to_vm: str, region=None, *args, **kwargs):
        if self.stop_command:
            self._run_shell_command(self.stop_command, "local stop command")
