"""midi_processing.timeline_generator

提供 MusicTimeline 类，封装音符对齐和时间线生成逻辑。
"""
from typing import List, Dict, Any
from .music_analyzer import align_notes


class MusicTimeline:
    def __init__(self, quantize: float = 0.125):
        self.quantize = quantize

    def align_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对音符做量化并合并重叠（调用 music_analyzer.align_notes）。"""
        return align_notes(notes, quantize=self.quantize)

    def handle_overlap(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """别名，保留与 align_notes 相同的行为。"""
        return self.align_notes(notes)

    def generate_sequence(self, mapped_tracks: Dict) -> List[Dict[str, Any]]:
        """简单地将映射的音轨事件合并成一个时间序列（按 start 排序）。
        mapped_tracks: {role: [events]}
        返回 List[events]
        """
        merged = []
        for role, evs in (mapped_tracks or {}).items():
            for ev in evs:
                ev2 = ev.copy()
                ev2['role'] = role
                merged.append(ev2)
        merged.sort(key=lambda x: x.get('start', 0.0))
        return merged
