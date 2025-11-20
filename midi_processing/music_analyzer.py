"""midi_processing.music_analyzer

提供乐理分析功能：
- 调性检测（基于音高类分布与 Krumhansl 轮廓）
- 简单和弦识别（窗口化）
- 节奏模式识别（IOI 直方图）
- 音符对齐/量化工具
"""
from typing import List, Dict, Tuple, Optional
import math
from collections import Counter, defaultdict
from .exceptions import InvalidInputError

# Krumhansl major/minor key profiles (normalized weights)
KRUMHANSL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KRUMHANSL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


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


def detect_key(events: List[Dict]) -> Optional[str]:
    """基于音高类持续时间分布识别调性，返回诸如 'C major' 或 'A minor'。

    Args:
        events: List of note events with 'note', 'start', and 'end' fields.

    Returns:
        Key signature string (e.g., 'C major', 'A minor') or None if key cannot be detected.

    Raises:
        InvalidInputError: If events list is empty or contains invalid data.
    """
    # Validate input
    if not events:
        raise InvalidInputError(
            "Cannot detect key from empty events list. Please provide at least one note event.",
            parameter_name="events",
            expected="Non-empty list of note events",
            received="Empty list"
        )

    if not isinstance(events, list):
        raise InvalidInputError(
            "Events must be a list.",
            parameter_name="events",
            expected="List of note events",
            received=f"{type(events).__name__}"
        )

    try:
        pc = _pitch_class_distribution(events)
    except InvalidInputError:
        raise  # Re-raise validation errors from _pitch_class_distribution

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
    """基于 onset 的 IOI（inter-onset interval）直方图，返回 top_k 常见间隔（秒）与其计数。

    Args:
        events: List of note events with 'start' field.
        top_k: Number of top patterns to return.

    Returns:
        List of (interval, count) tuples for the most common rhythmic intervals.

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

    if top_k <= 0:
        raise InvalidInputError(
            "top_k must be a positive integer.",
            parameter_name="top_k",
            expected="Positive integer",
            received=f"{top_k}"
        )

    # Validate event data and extract onsets
    for i, ev in enumerate(events):
        if 'start' not in ev:
            raise InvalidInputError(
                f"Event at index {i} is missing required 'start' field.",
                parameter_name="events",
                expected="Events with 'start' field"
            )

    try:
        onsets = sorted({ev['start'] for ev in events})
    except (TypeError, KeyError) as e:
        raise InvalidInputError(
            "Invalid event data: 'start' field must be a numeric value.",
            parameter_name="events",
            expected="Events with numeric 'start' values"
        )

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
