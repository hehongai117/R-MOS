"""
ModuleRegistry — registry for skill modules.

Verbatim move from orchestrator_v2.py (Phase 3 refactor).
"""

from typing import Dict, Any, List, Optional, Callable


class ModuleRegistry:
    """Registry for skill modules"""

    def __init__(self):
        self._modules: Dict[str, Callable] = {}
        self._module_metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        module_id: str,
        module_name: str,
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register a skill module"""
        self._modules[module_id] = handler
        self._module_metadata[module_id] = {
            "name": module_name,
            "metadata": metadata or {}
        }

    def get_handler(self, module_id: str) -> Optional[Callable]:
        """Get module handler by ID"""
        return self._modules.get(module_id)

    def get_metadata(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get module metadata"""
        return self._module_metadata.get(module_id)

    def list_modules(self) -> List[str]:
        """List all registered module IDs"""
        return list(self._modules.keys())
