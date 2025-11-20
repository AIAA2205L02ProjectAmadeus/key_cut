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
from typing import List, Dict, Tuple, Optional
import math
import os
import yaml
from collections import Counter, defaultdict
from .exceptions import InvalidInputError

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


def _pitch_class_distribution(events: List[Dict]) -> List[float]:
    """Calculate pitch class distribution from events.

    Args:
        events: List of note events with 'note', 'start', and 'end' fields.

    Returns:
        List of 12 normalized probabilities for each pitch class.

    Raises:
        InvalidInputError: If events list is empty or contains invalid data.
    """
    if not events:
        raise InvalidInputError(
            "Cannot calculate pitch class distribution from empty events list.",
            parameter_name="events",
            expected="Non-empty list of note events",
            received="Empty list"
        )

    pc = [0.0] * 12
    for i, ev in enumerate(events):
        # Validate required fields
        if 'note' not in ev:
            raise InvalidInputError(
                f"Event at index {i} is missing required 'note' field.",
                parameter_name="events",
                expected="Events with 'note', 'start', and 'end' fields"
            )
        if 'start' not in ev or 'end' not in ev:
            raise InvalidInputError(
                f"Event at index {i} is missing required 'start' or 'end' field.",
                parameter_name="events",
                expected="Events with 'note', 'start', and 'end' fields"
            )

        try:
            dur = max(0.0, ev.get('end', 0.0) - ev.get('start', 0.0))
            pc[ev['note'] % 12] += dur
        except (TypeError, ValueError) as e:
            raise InvalidInputError(
                f"Invalid note data at index {i}: note, start, and end must be numeric values.",
                parameter_name="events",
                expected="Numeric values for note, start, and end",
                received=f"note={ev.get('note')}, start={ev.get('start')}, end={ev.get('end')}"
            )

    s = sum(pc)
    if s > 0:
        pc = [x / s for x in pc]
    return pc


def detect_key(events: List[Dict]) -> str:
    """Detect the musical key of a piece using the Krumhansl-Schmuckler algorithm.

    This function analyzes the distribution of pitch classes weighted by note
    duration and correlates them with Krumhansl's major and minor key profiles
    for all 24 possible keys. The key with the highest correlation is returned.

    Args:
        events: List of note event dictionaries containing 'note', 'start',
            and 'end' fields.

    Returns:
        String representing the detected key (e.g., 'C major', 'A minor').
        Returns 'Unknown' if the key cannot be determined.

    Example:
        >>> events = parse_midi('song_in_c_major.mid')
        >>> key = detect_key(events)
        >>> print(key)
        'C major'

        >>> events = parse_midi('song_in_a_minor.mid')
        >>> detect_key(events)
        'A minor'

    Note:
        The algorithm works best with longer musical phrases containing
        clear tonal content. Short fragments or atonal music may produce
        ambiguous results.
    """
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

    # Return None if no key could be reliably detected
    if best is None or best_score <= 0:
        return None

    return f"{NOTE_NAMES[best[0]]} {best[1]}"


def analyze_chords(events: List[Dict], window: float = 0.5) -> List[Dict]:
    """简单窗口化和弦识别：每个窗口收集音高类，尝试匹配三和弦。
    返回 [{time, root, type, notes}]。

    Args:
        events: List of note events with 'note' and 'start' fields.
        window: Time window size in seconds for chord detection.

    Returns:
        List of detected chords with time, root, type, and notes.

    Raises:
        InvalidInputError: If events list is None or contains invalid data.
    """
    # Validate input
    if events is None:
        raise InvalidInputError(
            "Events cannot be None. Please provide a list of note events (can be empty).",
            parameter_name="events",
            expected="List of note events",
            received="None"
        )

    if not isinstance(events, list):
        raise InvalidInputError(
            "Events must be a list.",
            parameter_name="events",
            expected="List of note events",
            received=f"{type(events).__name__}"
        )

    if window <= 0:
        raise InvalidInputError(
            "Window size must be positive.",
            parameter_name="window",
            expected="Positive number",
            received=f"{window}"
        )

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
    try:
        onsets = sorted({ev['start'] for ev in events})
    except (TypeError, KeyError) as e:
        raise InvalidInputError(
            "Invalid event data: 'start' field must be a numeric value.",
            parameter_name="events",
            expected="Events with numeric 'start' values"
        )

    chords = []
    for t in onsets:
        # window: [t, t+window)
        try:
            notes = [ev['note'] % 12 for ev in events if ev['start'] >= t and ev['start'] < t + window]
        except (TypeError, KeyError) as e:
            raise InvalidInputError(
                "Invalid event data: 'note' field must be a numeric value.",
                parameter_name="events",
                expected="Events with numeric 'note' values"
            )

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
    """Analyze rhythm patterns using inter-onset interval (IOI) histogram.

    This function extracts the time intervals between consecutive note onsets
    and returns the most common intervals, which represent the dominant
    rhythmic patterns in the piece.

    Args:
        events: List of note event dictionaries containing 'start' field.
        top_k: Number of most common intervals to return. Default is 5.

    Returns:
        List of (interval, count) tuples, sorted by frequency (descending).
        Interval is in seconds (float), count is the number of occurrences.

    Example:
        >>> events = parse_midi('rhythmic_piece.mid')
        >>> patterns = rhythm_pattern(events, top_k=5)
        >>> for interval, count in patterns:
        ...     print(f"Interval: {interval}s, Count: {count}")
        Interval: 0.5s, Count: 234
        Interval: 0.25s, Count: 156
        Interval: 1.0s, Count: 89
        Interval: 0.75s, Count: 45
        Interval: 0.125s, Count: 23

    Note:
        At 120 BPM (quarter note = 0.5s):
        - 0.5s = quarter note
        - 0.25s = eighth note
        - 0.125s = sixteenth note
    """
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
    返回新的 events 列表（拷贝）。

    Args:
        events: List of note events with 'start', 'end', 'note', and 'channel' fields.
        quantize: Quantization grid size in seconds (must be positive).

    Returns:
        List of quantized and merged note events.

    Raises:
        InvalidInputError: If events list is None or contains invalid data.
    """
    # Validate input
    if events is None:
        raise InvalidInputError(
            "Events cannot be None. Please provide a list of note events (can be empty).",
            parameter_name="events",
            expected="List of note events",
            received="None"
        )

    if not isinstance(events, list):
        raise InvalidInputError(
            "Events must be a list.",
            parameter_name="events",
            expected="List of note events",
            received=f"{type(events).__name__}"
        )

    if quantize <= 0:
        raise InvalidInputError(
            "Quantize value must be positive.",
            parameter_name="quantize",
            expected="Positive number",
            received=f"{quantize}"
        )

    if not events:
        return []

    # Validate event data
    for i, ev in enumerate(events):
        required_fields = ['start', 'end', 'note', 'channel']
        for field in required_fields:
            if field not in ev:
                raise InvalidInputError(
                    f"Event at index {i} is missing required '{field}' field.",
                    parameter_name="events",
                    expected=f"Events with {', '.join(required_fields)} fields"
                )

    out = []
    for i, ev in enumerate(events):
        try:
            s = round(ev['start'] / quantize) * quantize
            e = round(ev['end'] / quantize) * quantize
            if e <= s:
                e = s + quantize  # 最小时值
            out.append({**ev, 'start': s, 'end': e})
        except (TypeError, ValueError) as e:
            raise InvalidInputError(
                f"Invalid numeric values in event at index {i}: start, end must be numbers.",
                parameter_name="events",
                expected="Numeric values for start and end",
                received=f"start={ev.get('start')}, end={ev.get('end')}"
            )

    # 合并完全重叠且相同 note/channel 的事件
    try:
        out.sort(key=lambda x: (x['note'], x['channel'], x['start']))
    except (TypeError, KeyError) as e:
        raise InvalidInputError(
            "Invalid event data: note and channel must be comparable values.",
            parameter_name="events"
        )

    merged = []
    for ev in out:
        if merged and ev['note'] == merged[-1]['note'] and ev['channel'] == merged[-1]['channel'] and ev['start'] <= merged[-1]['end']:
            # extend
            merged[-1]['end'] = max(merged[-1]['end'], ev['end'])
            merged[-1]['velocity'] = max(merged[-1]['velocity'], ev.get('velocity', 0))
        else:
            merged.append(ev.copy())
    return merged
