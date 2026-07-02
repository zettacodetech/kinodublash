"""Common speech data structures used across STT and dubbing stages."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechSegment:
    """A transcribed speech segment with chunk-relative timestamps."""

    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)
