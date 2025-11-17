"""midi_processing.music_analyzer

提供乐理分析功能：
- 调性检测（基于音高类分布与 Krumhansl 轮廓）
- 简单和弦识别（窗口化）
- 节奏模式识别（IOI 直方图）
- 音符对齐/量化工具
"""
from typing import List, Dict, Tuple
import math
from collections import Counter, defaultdict

# Krumhansl major/minor key profiles (normalized weights)
KRUMHANSL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KRUMHANSL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def _pitch_class_distribution(events: List[Dict]) -> List[float]:
    pc = [0.0] * 12
    for ev in events:
        dur = max(0.0, ev.get('end', 0.0) - ev.get('start', 0.0))
        pc[ev['note'] % 12] += dur
    s = sum(pc)
    if s > 0:
        pc = [x / s for x in pc]
    return pc


def detect_key(events: List[Dict]) -> str:
    """基于音高类持续时间分布识别调性，返回诸如 'C major' 或 'A minor'。"""
    pc = _pitch_class_distribution(events)
    best = None
    best_score = -1e9
    # 尝试所有 12 个移位，分别对 major/minor 轮廓做点积
    for root in range(12):
        # rotate profile
        major_profile = KRUMHANSL_MAJOR[-root:] + KRUMHANSL_MAJOR[:-root]
        minor_profile = KRUMHANSL_MINOR[-root:] + KRUMHANSL_MINOR[:-root]
        # compute correlation (dot product)
        maj_score = sum(a * b for a, b in zip(pc, major_profile))
        min_score = sum(a * b for a, b in zip(pc, minor_profile))
        if maj_score > best_score:
            best_score = maj_score
            best = (root, 'major')
        if min_score > best_score:
            best_score = min_score
            best = (root, 'minor')
    if best is None:
        return 'Unknown'
    return f"{NOTE_NAMES[best[0]]} {best[1]}"


def analyze_chords(events: List[Dict], window: float = 0.5) -> List[Dict]:
    """简单窗口化和弦识别：每个窗口收集音高类，尝试匹配三和弦。
    返回 [{time, root, type, notes}]。"""
    if not events:
        return []
    # 收集所有 onset times
    onsets = sorted({ev['start'] for ev in events})
    chords = []
    for t in onsets:
        # window: [t, t+window)
        notes = [ev['note'] % 12 for ev in events if ev['start'] >= t and ev['start'] < t + window]
        if not notes:
            continue
        pc = sorted(set(notes))
        # try all possible roots to classify triad
        found = False
        for root in pc:
            # compute intervals present
            intervals = set(((n - root) % 12) for n in pc)
            if {0, 4, 7}.issubset(intervals):
                chords.append({'time': t, 'root': NOTE_NAMES[root], 'type': 'major', 'notes': pc})
                found = True
                break
            if {0, 3, 7}.issubset(intervals):
                chords.append({'time': t, 'root': NOTE_NAMES[root], 'type': 'minor', 'notes': pc})
                found = True
                break
            if {0, 3, 6}.issubset(intervals):
                chords.append({'time': t, 'root': NOTE_NAMES[root], 'type': 'diminished', 'notes': pc})
                found = True
                break
        if not found:
            # fallback: record as cluster
            chords.append({'time': t, 'root': None, 'type': 'cluster', 'notes': pc})
    return chords


def rhythm_pattern(events: List[Dict], top_k: int = 5) -> List[Tuple[float, int]]:
    """基于 onset 的 IOI（inter-onset interval）直方图，返回 top_k 常见间隔（秒）与其计数。"""
    onsets = sorted({ev['start'] for ev in events})
    if len(onsets) < 2:
        return []
    iois = []
    for i in range(1, len(onsets)):
        iois.append(round(onsets[i] - onsets[i-1], 6))
    c = Counter(iois)
    return c.most_common(top_k)


def align_notes(events: List[Dict], quantize: float = 0.125) -> List[Dict]:
    """量化 start/end 到最近的 quantize（秒），并合并非常短的片段。
    返回新的 events 列表（拷贝）。"""
    out = []
    for ev in events:
        s = round(ev['start'] / quantize) * quantize
        e = round(ev['end'] / quantize) * quantize
        if e <= s:
            e = s + quantize  # 最小时值
        out.append({**ev, 'start': s, 'end': e})
    # 合并完全重叠且相同 note/channel 的事件
    out.sort(key=lambda x: (x['note'], x['channel'], x['start']))
    merged = []
    for ev in out:
        if merged and ev['note'] == merged[-1]['note'] and ev['channel'] == merged[-1]['channel'] and ev['start'] <= merged[-1]['end']:
            # extend
            merged[-1]['end'] = max(merged[-1]['end'], ev['end'])
            merged[-1]['velocity'] = max(merged[-1]['velocity'], ev.get('velocity', 0))
        else:
            merged.append(ev.copy())
    return merged
