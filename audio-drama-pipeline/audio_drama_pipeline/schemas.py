from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TranscriptLine:
    text: str
    start_time: float
    end_time: float
    speaker_id: str = "speaker_1"
    character_name: str = ""
    source: str = "asr"
    raw_speaker: str = ""
    pause_before: float = 0.0
    pause_after: float = 0.0
    speech_energy: float = 0.0
    pause_energy_before: float = 0.0
    pause_energy_after: float = 0.0
    music_bed_score: float = 0.0
    speaker_switch_before: bool = False
    speaker_switch_after: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Highlight:
    start_time: float
    end_time: float
    peak_time: float
    interaction_time: float
    highlight_type: str
    payoff_type: str
    key_line: str
    speaker_id: str
    character_name: str
    related_previous_events: List[Dict[str, Any]] = field(default_factory=list)
    trigger_reason: str = ""
    interaction_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EpisodeMemory:
    series_key: str
    episode_number: int
    episode_summary: str
    unresolved_threads: List[Dict[str, Any]] = field(default_factory=list)
    memory_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
