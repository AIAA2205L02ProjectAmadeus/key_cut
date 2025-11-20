"""midi_processing.music_analyzer

Provides music theory analysis functionality for MIDI note events.

Features:
- Key detection using Krumhansl-Schmuckler key-finding algorithm
- Simple chord recognition using window-based pitch class analysis
- Rhythm pattern identification via inter-onset interval (IOI) histograms
- Note alignment and quantization utilities

This module implements various music theory algorithms to extract high-level
musical information from low-level MIDI note events.
"""
from typing import List, Dict, Tuple, Any, Optional
import math
import os
import yaml
from collections import Counter, defaultdict
from .validators import (
    validate_note_events_list,
    validate_window_size,
    validate_top_k,
    validate_quantize_value,
    ValidationError
)

# Krumhansl major/minor key profiles (normalized weights)
KRUMHANSL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KRUMHANSL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# 默认配置值
DEFAULT_CHORD_WINDOW = 0.5
DEFAULT_QUANTIZE = 0.125
DEFAULT_RHYTHM_TOP_K = 5

# 全局配置变量（在加载配置后更新）
_config = {
    'chord_window': DEFAULT_CHORD_WINDOW,
    'quantize': DEFAULT_QUANTIZE,
    'rhythm_top_k': DEFAULT_RHYTHM_TOP_K,
}


def load_analysis_config(config_path: Optional[str] = None) -> Dict[str, float]:
    """从 YAML 文件加载分析配置。

    参数:
      - config_path: YAML 配置文件路径。如果为 None，则尝试加载默认的 analysis_config.yaml

    返回:
      - 配置字典 {'chord_window': float, 'quantize': float, 'rhythm_top_k': int}

    如果文件不存在或格式错误，返回默认值。
    """
    global _config

    # 如果没有指定 config_path，尝试加载默认配置文件
    if config_path is None:
        default_config = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'analysis_config.yaml')
        if os.path.exists(default_config):
            config_path = default_config

    if not config_path or not os.path.exists(config_path):
        # 文件不存在，使用默认值
        return _config.copy()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            doc = yaml.safe_load(f)
            if not doc or not isinstance(doc, dict):
                # 文件为空或格式不正确，使用默认值
                return _config.copy()

            # 更新配置，保持默认值作为后备
            loaded_config = {
                'chord_window': doc.get('chord_window', DEFAULT_CHORD_WINDOW),
                'quantize': doc.get('quantize', DEFAULT_QUANTIZE),
                'rhythm_top_k': doc.get('rhythm_top_k', DEFAULT_RHYTHM_TOP_K),
            }

            # 验证类型和合理性
            if not isinstance(loaded_config['chord_window'], (int, float)) or loaded_config['chord_window'] <= 0:
                loaded_config['chord_window'] = DEFAULT_CHORD_WINDOW
            if not isinstance(loaded_config['quantize'], (int, float)) or loaded_config['quantize'] <= 0:
                loaded_config['quantize'] = DEFAULT_QUANTIZE
            if not isinstance(loaded_config['rhythm_top_k'], int) or loaded_config['rhythm_top_k'] < 1:
                loaded_config['rhythm_top_k'] = DEFAULT_RHYTHM_TOP_K

            # 更新全局配置
            _config.update(loaded_config)
            return _config.copy()

    except (FileNotFoundError, IOError, yaml.YAMLError):
        # 文件读取错误或 YAML 解析错误，使用默认值
        return _config.copy()
    except Exception:
        # 其他未预期的错误，使用默认值
        return _config.copy()


def get_config() -> Dict[str, float]:
    """获取当前分析配置。

    返回:
      - 配置字典 {'chord_window': float, 'quantize': float, 'rhythm_top_k': int}
    """
    return _config.copy()


# 在模块加载时尝试加载默认配置
try:
    load_analysis_config()
except Exception:
    # 如果加载失败，保持默认值
    pass


def _pitch_class_distribution(events: List[Dict[str, Any]]) -> List[float]:
    """Calculate pitch class distribution weighted by duration.

    Args:
        events: List of note event dictionaries

    Returns:
        List of 12 normalized weights for pitch classes C through B
    """
    pc: List[float] = [0.0] * 12
    for ev in events:
        dur: float = max(0.0, ev.get('end', 0.0) - ev.get('start', 0.0))
        pc[ev['note'] % 12] += dur
    s: float = sum(pc)
    if s > 0:
        pc = [x / s for x in pc]
    return pc


def detect_key(events: List[Dict[str, Any]]) -> str:
    """基于音高类持续时间分布识别调性，返回诸如 'C major' 或 'A minor'。

    Args:
        events: List of note event dictionaries

    Returns:
        String describing detected key (e.g., 'C major', 'A minor')

    Raises:
        ValidationError: If events list is invalid
    """
    validate_note_events_list(events, strict=False)

    if not events:
        return 'Unknown'

    pc: List[float] = _pitch_class_distribution(events)
    best: Optional[Tuple[int, str]] = None
    best_score: float = -1e9
    # 尝试所有 12 个移位，分别对 major/minor 轮廓做点积
    for root in range(12):
        # rotate profile
        major_profile: List[float] = KRUMHANSL_MAJOR[-root:] + KRUMHANSL_MAJOR[:-root]
        minor_profile: List[float] = KRUMHANSL_MINOR[-root:] + KRUMHANSL_MINOR[:-root]
        # compute correlation (dot product)
        maj_score: float = sum(a * b for a, b in zip(pc, major_profile))
        min_score: float = sum(a * b for a, b in zip(pc, minor_profile))
        if maj_score > best_score:
            best_score = maj_score
            best = (root, 'major')
        if min_score > best_score:
            best_score = min_score
            best = (root, 'minor')

    # Return None if no key could be reliably detected
    if best is None or best_score <= 0:
        return None

    return f"{NOTE_NAMES[best[0]]} {best[1]}"


def analyze_chords(events: List[Dict[str, Any]], window: float = 0.5) -> List[Dict[str, Any]]:
    """简单窗口化和弦识别：每个窗口收集音高类，尝试匹配三和弦。
    返回 [{time, root, type, notes}]。

    Args:
        events: List of note event dictionaries
        window: Time window in seconds for chord analysis

    Returns:
        List of chord dictionaries with time, root, type, and notes

    Raises:
        ValidationError: If inputs are invalid
    """
    validate_note_events_list(events, strict=False)
    validate_window_size(window)

    if not events:
        return []

    # Validate event data
    for i, ev in enumerate(events):
        if 'note' not in ev:
            raise InvalidInputError(
                f"Event at index {i} is missing required 'note' field.",
                parameter_name="events",
                expected="Events with 'note' and 'start' fields"
            )
        if 'start' not in ev:
            raise InvalidInputError(
                f"Event at index {i} is missing required 'start' field.",
                parameter_name="events",
                expected="Events with 'note' and 'start' fields"
            )

    # 收集所有 onset times
    onsets: List[float] = sorted({ev['start'] for ev in events})
    chords: List[Dict[str, Any]] = []
    for t in onsets:
        # window: [t, t+window)
        notes: List[int] = [ev['note'] % 12 for ev in events if ev['start'] >= t and ev['start'] < t + window]
        if not notes:
            continue
        pc: List[int] = sorted(set(notes))
        # try all possible roots to classify triad
        found: bool = False
        for root in pc:
            # compute intervals present
            intervals: set[int] = set(((n - root) % 12) for n in pc)
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


def rhythm_pattern(events: List[Dict[str, Any]], top_k: int = 5) -> List[Tuple[float, int]]:
    """基于 onset 的 IOI（inter-onset interval）直方图，返回 top_k 常见间隔（秒）与其计数。

    Args:
        events: List of note event dictionaries
        top_k: Number of most common intervals to return

    Returns:
        List of (interval_seconds, count) tuples

    Raises:
        ValidationError: If inputs are invalid
    """
    validate_note_events_list(events, strict=False)
    validate_top_k(top_k)

    onsets: List[float] = sorted({ev['start'] for ev in events})
    if len(onsets) < 2:
        return []
    iois: List[float] = []
    for i in range(1, len(onsets)):
        iois.append(round(onsets[i] - onsets[i-1], 6))
    c: Counter[float] = Counter(iois)
    return c.most_common(top_k)


def align_notes(events: List[Dict[str, Any]], quantize: float = 0.125) -> List[Dict[str, Any]]:
    """量化 start/end 到最近的 quantize（秒），并合并非常短的片段。
    返回新的 events 列表（拷贝）。

    Args:
        events: List of note event dictionaries
        quantize: Quantization grid size in seconds

    Returns:
        New list of quantized and merged note events

    Raises:
        ValidationError: If inputs are invalid
    """
    validate_note_events_list(events, strict=False)
    validate_quantize_value(quantize)

    out: List[Dict[str, Any]] = []
    for ev in events:
        s: float = round(ev['start'] / quantize) * quantize
        e: float = round(ev['end'] / quantize) * quantize
        if e <= s:
            e = s + quantize  # 最小时值
        out.append({**ev, 'start': s, 'end': e})
    # 合并完全重叠且相同 note/channel 的事件
    out.sort(key=lambda x: (x['note'], x['channel'], x['start']))
    merged: List[Dict[str, Any]] = []
    for ev in out:
        if merged and ev['note'] == merged[-1]['note'] and ev['channel'] == merged[-1]['channel'] and ev['start'] <= merged[-1]['end']:
            # extend
            merged[-1]['end'] = max(merged[-1]['end'], ev['end'])
            merged[-1]['velocity'] = max(merged[-1]['velocity'], ev.get('velocity', 0))
        else:
            merged.append(ev.copy())
    return merged
