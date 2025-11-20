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
    if best is None:
        return 'Unknown'
    return f"{NOTE_NAMES[best[0]]} {best[1]}"


def analyze_chords(events: List[Dict], window: float = 0.5) -> List[Dict]:
    """Identify chords using window-based pitch class analysis.

    This function divides the musical timeline into windows and analyzes
    the pitch classes present in each window. It attempts to identify
    triads (major, minor, diminished) by checking for characteristic
    interval patterns.

    Args:
        events: List of note event dictionaries containing 'note' and 'start'.
        window: Time window size in seconds for grouping simultaneous notes.
            Default is 0.5 seconds.

    Returns:
        List of chord dictionaries, each containing:
        - time (float): Start time of the chord in seconds
        - root (str or None): Root note name (e.g., 'C', 'F#') or None
        - type (str): Chord type ('major', 'minor', 'diminished', 'cluster')
        - notes (list): List of pitch classes (0-11) present in the chord

    Example:
        >>> events = parse_midi('chord_progression.mid')
        >>> chords = analyze_chords(events, window=0.5)
        >>> for chord in chords[:3]:
        ...     print(f"{chord['time']:.2f}s: {chord['root']} {chord['type']}")
        0.00s: C major
        2.00s: F major
        4.00s: G major

    Note:
        - Adjust the window parameter based on tempo and musical style
        - Larger windows work better for slow music
        - Unrecognized pitch combinations are labeled as 'cluster'
    """
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
    """Quantize note timings to a rhythmic grid and merge overlapping notes.

    This function snaps note start and end times to the nearest quantization
    grid point and merges notes that overlap after quantization. This is
    useful for cleaning up timing imperfections or preparing data for
    analysis that assumes quantized rhythms.

    Args:
        events: List of note event dictionaries containing 'note', 'velocity',
            'start', 'end', and 'channel' fields.
        quantize: Grid spacing in seconds. Default is 0.125 (32nd note at 120 BPM).
            Common values:
            - 0.5 = quarter note at 120 BPM
            - 0.25 = eighth note at 120 BPM
            - 0.125 = sixteenth note at 120 BPM
            - 0.0625 = thirty-second note at 120 BPM

    Returns:
        New list of quantized event dictionaries (original events are not modified).
        Overlapping notes with the same pitch and channel are merged.

    Example:
        >>> events = parse_midi('slightly_off_timing.mid')
        >>> # Original timing
        >>> events[0]
        {'note': 60, 'start': 0.023, 'end': 0.487, ...}

        >>> # Quantized to 16th note grid
        >>> aligned = align_notes(events, quantize=0.125)
        >>> aligned[0]
        {'note': 60, 'start': 0.0, 'end': 0.5, ...}

    Note:
        - Very short notes (duration < quantize) are extended to minimum duration
        - Merging preserves the maximum velocity among merged notes
    """
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
