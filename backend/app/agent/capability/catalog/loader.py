from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.agent.capability.models.definitions import CapabilityDefinition
from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.capability.catalog.validator import (
    CapabilityCatalogLoadError,
    CapabilityValidator,
)
from app.agent.execution.tools.heat_treatment import build_langchain_tools


DEFAULT_DEFINITIONS_DIR = Path(__file__).with_name("definitions")


class CapabilityLoader:
    def __init__(
        self,
        definitions_dir: Path | str = DEFAULT_DEFINITIONS_DIR,
        executor_names: set[str] | None = None,
    ):
        self.definitions_dir = Path(definitions_dir)
        self.executor_names = executor_names

    def load(self) -> CapabilityRuntimeRegistry:
        capabilities = self.load_definitions()
        validator = CapabilityValidator(self._executor_names())
        validator.validate(capabilities)
        return CapabilityRuntimeRegistry(capabilities)

    def load_definitions(self) -> list[CapabilityDefinition]:
        if not self.definitions_dir.exists():
            raise CapabilityCatalogLoadError(
                f"Capability definitions directory does not exist: {self.definitions_dir}"
            )

        capabilities: list[CapabilityDefinition] = []
        files = sorted(
            [
                *self.definitions_dir.glob("*.yaml"),
                *self.definitions_dir.glob("*.yml"),
            ]
        )
        for path in files:
            capabilities.extend(self._load_file(path))
        return capabilities

    def _load_file(self, path: Path) -> list[CapabilityDefinition]:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise CapabilityCatalogLoadError(f"Invalid YAML in {path}: {exc}") from exc
        except OSError as exc:
            raise CapabilityCatalogLoadError(f"Cannot read capability file {path}: {exc}") from exc

        if raw is None:
            raise CapabilityCatalogLoadError(f"Capability file is empty: {path}")
        if not isinstance(raw, dict):
            raise CapabilityCatalogLoadError(f"Capability file root must be an object: {path}")

        raw_capabilities = raw.get("capabilities")
        if not isinstance(raw_capabilities, list):
            raise CapabilityCatalogLoadError(
                f"Capability file must contain a 'capabilities' list: {path}"
            )

        capabilities: list[CapabilityDefinition] = []
        for index, item in enumerate(raw_capabilities):
            if not isinstance(item, dict):
                raise CapabilityCatalogLoadError(
                    f"Capability entry #{index} in {path} must be an object"
                )
            capabilities.append(self._build_definition(item, path, index))
        return capabilities

    def _build_definition(
        self,
        raw: dict[str, Any],
        path: Path,
        index: int,
    ) -> CapabilityDefinition:
        try:
            return CapabilityDefinition.model_validate(raw)
        except ValidationError as exc:
            raise CapabilityCatalogLoadError(
                f"Invalid capability entry #{index} in {path}: {exc}"
            ) from exc

    def _executor_names(self) -> set[str]:
        if self.executor_names is not None:
            return self.executor_names
        return set(build_langchain_tools().keys())
