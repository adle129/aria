from pathlib import Path
from typing import Type

from app.services.generators.base import BaseGenerator


class GeneratorRegistry:
    _generators: dict[str, Type[BaseGenerator]] = {}

    @classmethod
    def register(cls, name: str, generator_cls: Type[BaseGenerator]) -> None:
        cls._generators[name] = generator_cls

    @classmethod
    def create(cls, name: str) -> BaseGenerator:
        if name not in cls._generators:
            raise KeyError(f"Unknown generator: {name}")
        return cls._generators[name]()
