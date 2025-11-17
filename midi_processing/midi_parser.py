"""midi_processing.midi_parser

提供基本的 MIDI 解析功能：
- 支持多轨（SMF）MIDI
- 处理 tempo 变化并将 ticks 转换为秒
- 提取 note_on/note_off 事件并输出带有 start/end 的事件列表
"""
from typing import List, Dict, Any, Tuple
import mido
import math


def _build_tempo_map(mid: mido.MidiFile) -> List[Tuple[int, int]]:
    """扫描所有 track，返回排序的 (absolute_tick, tempo) 列表。默认 tempo 500000 (120bpm)。"""
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
    """将绝对 ticks 转换为秒。处理分段 tempo。"""
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
    """解析 MIDI 文件，返回音符事件列表：
    每个事件为 dict: {note, velocity, start, end, channel, track, program}
    时间单位为秒（浮点）。
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
    """面向用户的高级解析器封装，提供类式 API。"""
    def __init__(self):
        pass

    def parse_midi_file(self, file_path: str) -> List[Dict[str, Any]]:
        """解析文件并返回 note event 列表（与 parse_midi 相同的格式）。"""
        return parse_midi(file_path)

    def extract_note_events(self, midi_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从 parse_midi 的输出中过滤并返回 note 事件（按 start 排序）。"""
        return sorted([e for e in midi_events if 'note' in e], key=lambda x: x['start'])

    def detect_tracks(self, file_path: str) -> List[Dict[str, Any]]:
        """检测并返回每个 track 的元信息（id, name, programs）。"""
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
