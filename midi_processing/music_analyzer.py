"""midi_processing.music_analyzer

提供乐理分析功能：
- 调性检测（基于音高类分布与 Krumhansl 轮廓）
- 简单和弦识别（窗口化）
- 节奏模式识别（IOI 直方图）
- 音符对齐/量化工具
"""
from typing import List, Dict, Tuple, Optional
import math
import os
import yaml
from collections import Counter, defaultdict

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


def analyze_chords(events: List[Dict], window: Optional[float] = None) -> List[Dict]:
    """简单窗口化和弦识别：每个窗口收集音高类，尝试匹配三和弦。
    返回 [{time, root, type, notes}]。

    参数:
      - events: 事件列表
      - window: 窗口大小（秒）。如果为 None，使用配置文件中的值或默认值
    """
    if window is None:
        window = _config['chord_window']

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


def rhythm_pattern(events: List[Dict], top_k: Optional[int] = None) -> List[Tuple[float, int]]:
    """基于 onset 的 IOI（inter-onset interval）直方图，返回 top_k 常见间隔（秒）与其计数。

    参数:
      - events: 事件列表
      - top_k: 返回前 k 个常见间隔。如果为 None，使用配置文件中的值或默认值
    """
    if top_k is None:
        top_k = _config['rhythm_top_k']

    onsets = sorted({ev['start'] for ev in events})
    if len(onsets) < 2:
        return []
    iois = []
    for i in range(1, len(onsets)):
        iois.append(round(onsets[i] - onsets[i-1], 6))
    c = Counter(iois)
    return c.most_common(top_k)


def align_notes(events: List[Dict], quantize: Optional[float] = None) -> List[Dict]:
    """量化 start/end 到最近的 quantize（秒），并合并非常短的片段。
    返回新的 events 列表（拷贝）。

    参数:
      - events: 事件列表
      - quantize: 量化步长（秒）。如果为 None，使用配置文件中的值或默认值
    """
    if quantize is None:
        quantize = _config['quantize']

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
