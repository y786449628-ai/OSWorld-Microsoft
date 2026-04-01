import logging
import os
import platform
import subprocess
import time

from desktop_env.providers.base import Provider

logger = logging.getLogger("desktopenv.providers.vmware.VMwareProvider")
logger.setLevel(logging.INFO)

WAIT_TIME = 3


def get_vmrun_type(return_list=False):
    if platform.system() == "Windows" or platform.system() == "Linux":
        if return_list:
            return ["-T", "ws"]
        return "-T ws"
    elif platform.system() == "Darwin":
        if return_list:
            return ["-T", "fusion"]
        return "-T fusion"
    else:
        raise Exception("Unsupported operating system")


def get_vmrun_base_command():
    """
    Build the base vmrun command.

    If OSWORLD_VMWARE_VM_PASSWORD is set, append -vp <password>
    so encrypted VMware VMs can be controlled non-interactively.

    If not set, behavior remains identical to the old implementation.
    """
    cmd = ["vmrun"] + get_vmrun_type(return_list=True)
    vm_password = os.environ.get("OSWORLD_VMWARE_VM_PASSWORD")
    if vm_password:
        cmd += ["-vp", vm_password]
    return cmd


class VMwareProvider(Provider):

    @staticmethod
    def _execute_command(command: list, return_output=False):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            err = (stderr or stdout or "").strip()
            raise RuntimeError(err)

        if return_output:
            return (stdout or "").strip()

        return None

    def start_emulator(self, path_to_vm: str, headless: bool, os_type: str):
        logger.info("Starting VMware VM...")

        while True:
            try:
                output = subprocess.check_output(
                    get_vmrun_base_command() + ["list"],
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8"
                )
                output_lines = output.splitlines()
                normalized_path_to_vm = os.path.abspath(os.path.normpath(path_to_vm))

                # vmrun list output contains:
                # line 0 => "Total running VMs: X"
                # following lines => running vmx paths
                running_vms = [
                    os.path.abspath(os.path.normpath(line.strip()))
                    for line in output_lines[1:]
                    if line.strip()
                ]

                if normalized_path_to_vm in running_vms:
                    logger.info("VM is running.")
                    break

                logger.info("VM is not running. Starting VM...")
                command = get_vmrun_base_command() + ["start", path_to_vm]
                if headless:
                    command.append("nogui")

                self._execute_command(command)
                time.sleep(WAIT_TIME)

            except subprocess.CalledProcessError as e:
                logger.error(f"Error checking running VMs: {e.output}")
                time.sleep(WAIT_TIME)
            except Exception as e:
                logger.error(f"Error starting VM: {e}")
                time.sleep(WAIT_TIME)

    def get_ip_address(self, path_to_vm: str) -> str:
        logger.info("Getting VMware VM IP address...")

        while True:
            try:
                output = self._execute_command(
                    get_vmrun_base_command() + ["getGuestIPAddress", path_to_vm, "-wait"],
                    return_output=True
                )
                logger.info(f"VMware VM IP address: {output}")
                return output
            except Exception as e:
                logger.error(f"Error getting VMware VM IP address: {e}")
                time.sleep(WAIT_TIME)
                logger.info("Retrying to get VMware VM IP address...")

    def save_state(self, path_to_vm: str, snapshot_name: str):
        logger.info("Saving VMware VM state...")
        self._execute_command(
            get_vmrun_base_command() + ["snapshot", path_to_vm, snapshot_name]
        )
        time.sleep(WAIT_TIME)

    def revert_to_snapshot(self, path_to_vm: str, snapshot_name: str):
        logger.info(f"Reverting VMware VM to snapshot: {snapshot_name}...")
        self._execute_command(
            get_vmrun_base_command() + ["revertToSnapshot", path_to_vm, snapshot_name]
        )
        time.sleep(WAIT_TIME)
        return path_to_vm

    def stop_emulator(self, path_to_vm: str, region=None, *args, **kwargs):
        logger.info("Stopping VMware VM...")
        self._execute_command(
            get_vmrun_base_command() + ["stop", path_to_vm]
        )
        time.sleep(WAIT_TIME)