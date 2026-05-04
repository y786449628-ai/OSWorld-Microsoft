import os

from desktop_env.providers.base import VMManager


class LocalVMManager(VMManager):
    def __init__(self, registry_path: str = ""):
        self.registry_path = registry_path
        self.initialize_registry()

    def initialize_registry(self, **kwargs):
        return None

    def add_vm(self, vm_path, **kwargs):
        return None

    def delete_vm(self, vm_path, **kwargs):
        return None

    def occupy_vm(self, vm_path, pid, **kwargs):
        return None

    def list_free_vms(self, **kwargs):
        return "local"

    def check_and_clean(self, **kwargs):
        return None

    def get_vm_path(self, **kwargs):
        return os.getenv("OSWORLD_LOCAL_VM_ID", "local")
