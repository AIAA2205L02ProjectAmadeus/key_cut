"""midi_processing.timeline_generator

Provides the MusicTimeline class for note alignment and timeline generation.

This module encapsulates note quantization and timeline sequence generation
logic, offering a convenient interface for creating properly aligned musical
timelines from raw MIDI events.
"""
from typing import List, Dict, Any
from .music_analyzer import align_notes


class MusicTimeline:
    """Timeline generator for aligning and sequencing musical events.

    This class provides utilities for quantizing note timings and generating
    chronological sequences from mapped track events. It's useful for creating
    aligned timelines for visualization or further processing.

    Attributes:
        quantize: Grid spacing in seconds for note alignment.

    Example:
        >>> timeline = MusicTimeline(quantize=0.125)
        >>> events = parse_midi('song.mid')
        >>> aligned = timeline.align_notes(events)
        >>>
        >>> # Generate sequence from mapped tracks
        >>> mapper = TrackMapper()
        >>> mapping = mapper.auto_map_tracks(events=events)
        >>> # Group events by role
        >>> mapped_tracks = {}
        >>> for ev in events:
        ...     role = mapping.get(ev.get('track_name', f"track_{ev['track']}"), 'unknown')
        ...     if role not in mapped_tracks:
        ...         mapped_tracks[role] = []
        ...     mapped_tracks[role].append(ev)
        >>> sequence = timeline.generate_sequence(mapped_tracks)
    """
    def __init__(self, quantize: float = 0.125):
        """Initialize the MusicTimeline.

        Args:
            quantize: Grid spacing in seconds for note alignment.
                Default is 0.125 (32nd note at 120 BPM).
        """
        self.quantize = quantize

    def align_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Quantize and merge overlapping notes.

        This is a wrapper around music_analyzer.align_notes using the
        instance's quantize parameter.

        Args:
            notes: List of note event dictionaries.

        Returns:
            List of quantized and merged note events.

        Example:
            >>> timeline = MusicTimeline(quantize=0.25)
            >>> aligned = timeline.align_notes(events)
        """
        return align_notes(notes, quantize=self.quantize)

    def handle_overlap(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle overlapping notes (alias for align_notes).

        Args:
            notes: List of note event dictionaries.

        Returns:
            List of quantized and merged note events.
        """
        return self.align_notes(notes)

    def generate_sequence(self, mapped_tracks: Dict) -> List[Dict[str, Any]]:
        """Generate a chronological sequence from mapped track events.

        This method merges events from multiple tracks/roles into a single
        time-ordered sequence, adding a 'role' field to each event.

        Args:
            mapped_tracks: Dictionary mapping roles to event lists.
                Format: {role: [events]}

        Returns:
            Single merged list of events sorted by start time, with each
            event containing an additional 'role' field.

        Example:
            >>> mapped_tracks = {
            ...     'piano': [{'note': 60, 'start': 0.0, ...}],
            ...     'bass': [{'note': 48, 'start': 0.0, ...}]
            ... }
            >>> timeline = MusicTimeline()
            >>> sequence = timeline.generate_sequence(mapped_tracks)
            >>> sequence[0]['role']
            'piano'
        """
        merged = []
        for role, evs in (mapped_tracks or {}).items():
            for ev in evs:
                ev2 = ev.copy()
                ev2['role'] = role
                merged.append(ev2)
        merged.sort(key=lambda x: x.get('start', 0.0))
        return merged
