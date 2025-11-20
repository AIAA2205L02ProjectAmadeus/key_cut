"""midi_processing.analysis_result

Data class for storing music analysis results.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """Container for music analysis results."""

    key: Optional[str] = None
    chords: List[Dict[str, Any]] = field(default_factory=list)
    rhythm_patterns: List[tuple] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    track_mapping: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary.

        Returns:
            Dictionary representation of analysis result
        """
        return {
            'key': self.key,
            'chords': self.chords,
            'rhythm_patterns': self.rhythm_patterns,
            'events': self.events,
            'track_mapping': self.track_mapping,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create AnalysisResult from dictionary.

        Args:
            data: Dictionary containing analysis data

        Returns:
            AnalysisResult instance
        """
        return cls(
            key=data.get('key'),
            chords=data.get('chords', []),
            rhythm_patterns=data.get('rhythm_patterns', []),
            events=data.get('events', []),
            track_mapping=data.get('track_mapping', {}),
            metadata=data.get('metadata', {}),
        )
