"""midi_processing.timeline_generator

Provides the MusicTimeline class for note alignment and timeline generation.

This module encapsulates note quantization and timeline sequence generation
logic, offering a convenient interface for creating properly aligned musical
timelines from raw MIDI events.
"""
from typing import List, Dict, Any, Optional
from .music_analyzer import align_notes
from .validators import validate_quantize_value, validate_note_events_list, ValidationError


class MusicTimeline:
    """Music timeline generator with quantization and sequence generation capabilities."""

    def __init__(self, quantize: float = 0.125) -> None:
        """Initialize MusicTimeline.

        Args:
            quantize: Quantization grid size in seconds

        Raises:
            ValidationError: If quantize value is invalid
        """
        validate_quantize_value(quantize)
        self.quantize: float = quantize

    def align_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对音符做量化并合并重叠（调用 music_analyzer.align_notes）。

        Args:
            notes: List of note event dictionaries

        Returns:
            Quantized and merged list of note events

        Raises:
            ValidationError: If notes list is invalid
        """
        validate_note_events_list(notes, strict=False)
        return align_notes(notes, quantize=self.quantize)

    def handle_overlap(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """别名，保留与 align_notes 相同的行为。

        Args:
            notes: List of note event dictionaries

        Returns:
            Quantized and merged list of note events

        Raises:
            ValidationError: If notes list is invalid
        """
        return self.align_notes(notes)

    def generate_sequence(self, mapped_tracks: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """简单地将映射的音轨事件合并成一个时间序列（按 start 排序）。
        mapped_tracks: {role: [events]}
        返回 List[events]

        Args:
            mapped_tracks: Dictionary mapping role names to lists of note events

        Returns:
            Merged and sorted list of all events with role annotations

        Raises:
            ValidationError: If mapped_tracks is not a dictionary
        """
        if not isinstance(mapped_tracks, dict):
            raise ValidationError(f"mapped_tracks must be a dictionary, got {type(mapped_tracks).__name__}")

        merged: List[Dict[str, Any]] = []
        for role, evs in (mapped_tracks or {}).items():
            if not isinstance(evs, list):
                continue
            for ev in evs:
                if not isinstance(ev, dict):
                    continue
                ev2: Dict[str, Any] = ev.copy()
                ev2['role'] = role
                merged.append(ev2)
        merged.sort(key=lambda x: x.get('start', 0.0))
        return merged
