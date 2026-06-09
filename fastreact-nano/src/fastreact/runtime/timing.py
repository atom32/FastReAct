"""Small timing helpers used by runtime and release-gate tests."""

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


def now_ms() -> float:
    """Return a monotonic timestamp in milliseconds."""
    return perf_counter() * 1000


@dataclass
class TimingSpan:
    """Record elapsed time for a named runtime span."""

    name: str
    start_ms: float = field(default_factory=now_ms)
    end_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, **metadata: Any) -> "TimingSpan":
        """Mark the span as complete and attach optional metadata."""
        self.end_ms = now_ms()
        self.metadata.update(metadata)
        return self

    @property
    def elapsed_ms(self) -> float:
        """Return elapsed milliseconds, using now if the span is open."""
        return (self.end_ms or now_ms()) - self.start_ms

    def to_dict(self) -> dict[str, Any]:
        """Serialize the span without leaking request content."""
        return {
            "name": self.name,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "metadata": self.metadata,
        }
