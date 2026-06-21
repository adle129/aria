from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, context: dict[str, Any], template_path: Path, output_path: Path) -> Path:
        """Generate output file from template and context."""
