"""midi_processing.midi_parser

Provides basic MIDI parsing functionality for Standard MIDI Files (SMF).

Features:
- Multi-track MIDI file support
- Tempo change handling with accurate tick-to-seconds conversion
- Note event extraction (note_on/note_off) with start/end timestamps

This module handles the low-level parsing of MIDI files, converting raw MIDI
messages into a structured list of note events with timing information in seconds.
"""
from typing import List, Dict, Any, Tuple, Optional
import mido
import math
from .validators import (
    validate_midi_file_path,
    validate_ticks_per_beat,
    validate_tempo,
    ValidationError
)
import os
from .exceptions import MIDIParsingError


def _build_tempo_map(mid: mido.MidiFile) -> List[Tuple[int, int]]:
    """扫描所有 track，返回排序的 (absolute_tick, tempo) 列表。默认 tempo 500000 (120bpm)。

    Args:
        mid: mido.MidiFile object

    Returns:
        List of (absolute_tick, tempo) tuples sorted by tick

    Raises:
        ValidationError: If invalid tempo values are encountered
    """
    tempo_map: List[Tuple[int, int]] = [(0, 500000)]
    for i, track in enumerate(mid.tracks):
        abs_tick: int = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                validate_tempo(msg.tempo)
                tempo_map.append((abs_tick, msg.tempo))
    tempo_map.sort(key=lambda x: x[0])
    return tempo_map


def _ticks_to_seconds(ticks: int, tempo_map: List[Tuple[int, int]], ticks_per_beat: int) -> float:
    """将绝对 ticks 转换为秒。处理分段 tempo。

    Args:
        ticks: Absolute tick count
        tempo_map: List of (tick, tempo) tuples
        ticks_per_beat: Ticks per beat from MIDI file

    Returns:
        Time in seconds

    Raises:
        ValidationError: If ticks_per_beat is invalid
    """
    validate_ticks_per_beat(ticks_per_beat)

    if ticks <= 0:
        return 0.0
    seconds: float = 0.0
    last_tick: int = 0
    for i, (tempo_tick, tempo) in enumerate(tempo_map):
        if ticks <= tempo_tick:
            # all remaining ticks are under previous tempo
            dt: int = ticks - last_tick
            seconds += dt * (tempo_map[i-1][1] / 1000000.0) / ticks_per_beat
            return seconds
        else:
            if tempo_tick > last_tick:
                dt = tempo_tick - last_tick
                seconds += dt * (tempo_map[i-1][1] / 1000000.0) / ticks_per_beat
            last_tick = tempo_tick
    # if we reach here, use last tempo for remaining
    last_tempo: int = tempo_map[-1][1]
    dt = ticks - last_tick
    seconds += dt * (last_tempo / 1000000.0) / ticks_per_beat
    return seconds


def parse_midi(path: str) -> List[Dict[str, Any]]:
    """解析 MIDI 文件，返回音符事件列表：
    每个事件为 dict: {note, velocity, start, end, channel, track, program}
    时间单位为秒（浮点）。

    Args:
        path: Path to MIDI file

    Returns:
        List of note event dictionaries

    Raises:
        ValidationError: If file path is invalid or file cannot be read
        OSError: If file cannot be opened
    """
    validate_midi_file_path(path)

    mid: mido.MidiFile = mido.MidiFile(path)
    ticks_per_beat: int = mid.ticks_per_beat
    validate_ticks_per_beat(ticks_per_beat)
    tempo_map: List[Tuple[int, int]] = _build_tempo_map(mid)

    events: List[Dict[str, Any]] = []
    # 为每条 track 单独扫描，以保留 track id 和 track 名称
    for ti, track in enumerate(mid.tracks):
        abs_tick: int = 0
        track_name: Optional[str] = None
        # open_notes: key=(channel,note) -> (start_tick, velocity, program)
        open_notes: Dict[Tuple[int, int], Tuple[int, int, int]] = {}
        current_program: Optional[int] = None
        for msg in track:
            abs_tick += msg.time
            # 捕获 track name（MetaMessage 'track_name' 在 mido 中通常有 name 或 text 属性）
            if getattr(msg, 'type', None) == 'track_name':
                track_name = getattr(msg, 'name', getattr(msg, 'text', None))
            if msg.type == 'program_change':
                current_program = msg.program
            if msg.type == 'note_on' and msg.velocity > 0:
                key: Tuple[int, int] = (getattr(msg, 'channel', 0), msg.note)
                open_notes[key] = (abs_tick, msg.velocity, current_program if current_program is not None else -1)
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                key = (getattr(msg, 'channel', 0), msg.note)
                if key in open_notes:
                    start_tick: int
                    velocity: int
                    program: int
                    start_tick, velocity, program = open_notes.pop(key)
                    start_sec: float = _ticks_to_seconds(start_tick, tempo_map, ticks_per_beat)
                    end_sec: float = _ticks_to_seconds(abs_tick, tempo_map, ticks_per_beat)
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
    """面向用户的高级解析器封装，提供类式 API。"""
    def __init__(self) -> None:
        pass

    def parse_midi_file(self, file_path: str) -> List[Dict[str, Any]]:
        """解析文件并返回 note event 列表（与 parse_midi 相同的格式）。

        Args:
            file_path: Path to MIDI file

        Returns:
            List of note event dictionaries

        Raises:
            ValidationError: If file path is invalid
        """
        return parse_midi(file_path)

    def extract_note_events(self, midi_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从 parse_midi 的输出中过滤并返回 note 事件（按 start 排序）。

        Args:
            midi_events: List of MIDI event dictionaries

        Returns:
            Filtered and sorted list of note events
        """
        return sorted([e for e in midi_events if 'note' in e], key=lambda x: x['start'])

    def detect_tracks(self, file_path: str) -> List[Dict[str, Any]]:
        """检测并返回每个 track 的元信息（id, name, programs）。

        Args:
            file_path: Path to MIDI file

        Returns:
            List of track metadata dictionaries

        Raises:
            ValidationError: If file path is invalid
        """
        validate_midi_file_path(file_path)

        mid: mido.MidiFile = mido.MidiFile(file_path)
        tracks: List[Dict[str, Any]] = []
        for ti, track in enumerate(mid.tracks):
            track_name: Optional[str] = None
            programs: set[int] = set()
            for msg in track:
                if getattr(msg, 'type', None) == 'track_name':
                    track_name = getattr(msg, 'name', getattr(msg, 'text', None))
                if getattr(msg, 'type', None) == 'program_change':
                    programs.add(getattr(msg, 'program', -1))
            tracks.append({'track_id': ti, 'track_name': track_name, 'programs': sorted(list(programs))})
        return tracks
