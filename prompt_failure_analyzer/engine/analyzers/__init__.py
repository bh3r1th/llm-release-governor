from dataclasses import dataclass


@dataclass
class Finding:
    analyzer: str
    severity: str
    pattern: str
    message: str
    line: int | None

