"""midi_processing.midi_parser

Provides basic MIDI parsing functionality for Standard MIDI Files (SMF).

Features:
- Multi-track MIDI file support
- Tempo change handling with accurate tick-to-seconds conversion
- Note event extraction (note_on/note_off) with start/end timestamps

This module handles the low-level parsing of MIDI files, converting raw MIDI
messages into a structured list of note events with timing information in seconds.
"""
from typing import List, Dict, Any, Tuple
import mido
import math


def _build_tempo_map(mid: mido.MidiFile) -> List[Tuple[int, int]]:
    """Build a tempo map by scanning all tracks for tempo changes.

    Args:
        mid: A mido.MidiFile object containing MIDI tracks.

    Returns:
        A sorted list of (absolute_tick, tempo) tuples. The tempo is in microseconds
        per quarter note. Default tempo is 500000 (120 BPM).

    Example:
        >>> mid = mido.MidiFile('song.mid')
        >>> tempo_map = _build_tempo_map(mid)
        >>> tempo_map
        [(0, 500000), (1920, 428571)]  # Tempo change at tick 1920
    """
    tempo_map = [(0, 500000)]
    for i, track in enumerate(mid.tracks):
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                tempo_map.append((abs_tick, msg.tempo))
    tempo_map.sort(key=lambda x: x[0])
    return tempo_map


def _ticks_to_seconds(ticks: int, tempo_map: List[Tuple[int, int]], ticks_per_beat: int) -> float:
    """Convert absolute MIDI ticks to seconds, handling tempo changes.

    This function accounts for tempo changes throughout the MIDI file by using
    a tempo map. It calculates the cumulative time by processing each tempo
    segment separately.

    Args:
        ticks: Absolute tick value to convert.
        tempo_map: List of (tick, tempo) tuples from _build_tempo_map.
        ticks_per_beat: MIDI file's ticks per quarter note resolution.

    Returns:
        Time in seconds (float) corresponding to the given tick position.

    Example:
        >>> tempo_map = [(0, 500000), (1920, 428571)]
        >>> _ticks_to_seconds(960, tempo_map, 480)
        1.0  # 960 ticks = 2 beats at 120 BPM = 1 second
    """
    if ticks <= 0:
        return 0.0
    seconds = 0.0
    last_tick = 0
    for i, (tempo_tick, tempo) in enumerate(tempo_map):
        if ticks <= tempo_tick:
            # all remaining ticks are under previous tempo
            dt = ticks - last_tick
            seconds += dt * (tempo_map[i-1][1] / 1000000.0) / ticks_per_beat
            return seconds
        else:
            if tempo_tick > last_tick:
                dt = tempo_tick - last_tick
                seconds += dt * (tempo_map[i-1][1] / 1000000.0) / ticks_per_beat
            last_tick = tempo_tick
    # if we reach here, use last tempo for remaining
    last_tempo = tempo_map[-1][1]
    dt = ticks - last_tick
    seconds += dt * (last_tempo / 1000000.0) / ticks_per_beat
    return seconds


def parse_midi(path: str) -> List[Dict[str, Any]]:
    """Parse a MIDI file and return a list of note events.

    This is the main entry point for parsing MIDI files. It extracts all note
    events from all tracks, converts timing information to seconds, and returns
    a structured list of note events sorted by start time.

    Args:
        path: File path to the MIDI file to parse.

    Returns:
        A list of note event dictionaries, each containing:
        - note (int): MIDI note number (0-127)
        - velocity (int): Note velocity (1-127)
        - start (float): Note start time in seconds
        - end (float): Note end time in seconds
        - channel (int): MIDI channel (0-15)
        - track (int): Track index in the MIDI file
        - track_name (str or None): Name of the track (if available)
        - program (int): MIDI program/instrument number (-1 if not set)

    Example:
        >>> events = parse_midi('song.mid')
        >>> events[0]
        {'note': 60, 'velocity': 80, 'start': 0.0, 'end': 0.5,
         'channel': 0, 'track': 1, 'track_name': 'Piano', 'program': 0}
        >>> print(f"First note: {events[0]['note']} at {events[0]['start']}s")
        First note: 60 at 0.0s
    """
    mid = mido.MidiFile(path)
    ticks_per_beat = mid.ticks_per_beat
    tempo_map = _build_tempo_map(mid)

    events: List[Dict[str, Any]] = []
    # 为每条 track 单独扫描，以保留 track id 和 track 名称
    for ti, track in enumerate(mid.tracks):
        abs_tick = 0
        track_name = None
        # open_notes: key=(channel,note) -> (start_tick, velocity, program)
        open_notes: Dict[Tuple[int, int], Tuple[int, int, int]] = {}
        current_program = None
        for msg in track:
            abs_tick += msg.time
            # 捕获 track name（MetaMessage 'track_name' 在 mido 中通常有 name 或 text 属性）
            if getattr(msg, 'type', None) == 'track_name':
                track_name = getattr(msg, 'name', getattr(msg, 'text', None))
            if msg.type == 'program_change':
                current_program = msg.program
            if msg.type == 'note_on' and msg.velocity > 0:
                key = (getattr(msg, 'channel', 0), msg.note)
                open_notes[key] = (abs_tick, msg.velocity, current_program if current_program is not None else -1)
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                key = (getattr(msg, 'channel', 0), msg.note)
                if key in open_notes:
                    start_tick, velocity, program = open_notes.pop(key)
                    start_sec = _ticks_to_seconds(start_tick, tempo_map, ticks_per_beat)
                    end_sec = _ticks_to_seconds(abs_tick, tempo_map, ticks_per_beat)
                    events.append({
                        'note': msg.note,
                        'velocity': velocity,
                        'start': start_sec,
                        'end': end_sec,
                        'channel': key[0],
                        'track': ti,
                        'track_name': track_name,
                        'program': program,
                    })
                else:
                    # 未匹配的 note_off：忽略或记录为零长度
                    pass
    # 按 start 排序
    events.sort(key=lambda e: e['start'])
    return events


class AdvancedMIDIParser:
    """Advanced MIDI parser providing a class-based API.

    This class wraps the parse_midi function and provides additional utilities
    for track detection and event filtering. Use this class when you need
    object-oriented interface or track metadata extraction.

    Example:
        >>> parser = AdvancedMIDIParser()
        >>> events = parser.parse_midi_file('song.mid')
        >>> tracks = parser.detect_tracks('song.mid')
        >>> for track in tracks:
        ...     print(f"Track {track['track_id']}: {track['track_name']}")
    """
    def __init__(self):
        """Initialize the AdvancedMIDIParser."""
        pass

    def parse_midi_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a MIDI file and return note events.

        Args:
            file_path: Path to the MIDI file.

        Returns:
            List of note event dictionaries (same format as parse_midi).

        Example:
            >>> parser = AdvancedMIDIParser()
            >>> events = parser.parse_midi_file('example.mid')
            >>> len(events)
            1523
        """
        return parse_midi(file_path)

    def extract_note_events(self, midi_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and return only note events from parsed MIDI events.

        Args:
            midi_events: List of MIDI events from parse_midi.

        Returns:
            Filtered list of note events, sorted by start time.

        Note:
            This method is primarily for compatibility. The parse_midi function
            already returns only note events.
        """
        return sorted([e for e in midi_events if 'note' in e], key=lambda x: x['start'])

    def detect_tracks(self, file_path: str) -> List[Dict[str, Any]]:
        """Detect and return metadata for each track in a MIDI file.

        Args:
            file_path: Path to the MIDI file.

        Returns:
            List of track metadata dictionaries, each containing:
            - track_id (int): Zero-based track index
            - track_name (str or None): Track name from track_name meta message
            - programs (list): Sorted list of program numbers used in the track

        Example:
            >>> parser = AdvancedMIDIParser()
            >>> tracks = parser.detect_tracks('song.mid')
            >>> tracks[1]
            {'track_id': 1, 'track_name': 'Piano', 'programs': [0, 1]}
        """
        mid = mido.MidiFile(file_path)
        tracks = []
        for ti, track in enumerate(mid.tracks):
            track_name = None
            programs = set()
            for msg in track:
                if getattr(msg, 'type', None) == 'track_name':
                    track_name = getattr(msg, 'name', getattr(msg, 'text', None))
                if getattr(msg, 'type', None) == 'program_change':
                    programs.add(getattr(msg, 'program', -1))
            tracks.append({'track_id': ti, 'track_name': track_name, 'programs': sorted(list(programs))})
        return tracks
