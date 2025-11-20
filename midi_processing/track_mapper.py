"""midi_processing.track_mapper

Implements automatic track mapping based on track names and instrument programs.

This module provides flexible track-to-role mapping using configurable regex
patterns. It supports both manual mapping rules and YAML configuration files.
Track names or MIDI program numbers can be used to categorize tracks into
musical roles (e.g., piano, bass, drums, melody).
"""
from typing import List, Dict, Tuple, Optional, Any
import re
from .validators import validate_track_mapping, validate_config_path, ValidationError
from .exceptions import ConfigurationError
import os
import yaml

DEFAULT_RULES: List[Tuple[str, str]] = [
    (r'piano|grand', 'piano'),
    (r'guitar', 'guitar'),
    (r'bass', 'bass'),
    (r'drum|perc', 'drums'),
    (r'violin|cello|strings', 'strings'),
    (r'flute|sax|clarinet', 'winds'),
]


def map_tracks(track_names: List[str], rules: Optional[List[Tuple[str, str]]] = None) -> Dict[str, str]:
    """根据轨道名称返回映射：{原名: mapped_role}

    参数:
      - track_names: 轨道名称列表
      - rules: 可选的 (pattern, target) 列表（按顺序匹配）

    默认行为：按规则匹配，未匹配则使用 'unknown'

    Args:
        track_names: List of track names to map
        rules: Optional list of (regex_pattern, target_role) tuples

    Returns:
        Dictionary mapping track names to role names

    Raises:
        ValidationError: If inputs are invalid
    """
    if not isinstance(track_names, list):
        raise ValidationError(f"track_names must be a list, got {type(track_names).__name__}")

    rules = rules or DEFAULT_RULES
    compiled: List[Tuple[re.Pattern[str], str]] = [(re.compile(pat, re.IGNORECASE), target) for pat, target in rules]
    mapping: Dict[str, str] = {}
    for name in track_names:
        assigned: str = 'unknown'
        for cre, target in compiled:
            if cre.search(name or ''):
                assigned = target
                break
        mapping[name] = assigned

    return mapping


def map_tracks_from_parser_events(events: List[Dict[str, Any]]) -> Dict[int, str]:
    """辅助函数：从解析器事件中基于 track id 提取名字并映射。
    解析器当前只提供 track id，若没有名字则使用 'track_{id}'。
    返回 {track_id: role}

    Args:
        events: List of note event dictionaries from parser

    Returns:
        Dictionary mapping track IDs to role names

    Raises:
        ValidationError: If events is not a list
    """
    if not isinstance(events, list):
        raise ValidationError(f"events must be a list, got {type(events).__name__}")

    # 这里我们没有 track 名称信息，因此返回 default roles per program if available
    # 作为后备策略：如果存在 program 字段，按 program 范围推测（简化）
    mapping: Dict[int, str] = {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        tid: int = ev.get('track', 0)
        if tid in mapping:
            continue
        program: Optional[int] = ev.get('program', -1)
        role: str = 'unknown'
        if program is not None and program >= 0:
            if 0 <= program <= 7:
                role = 'piano'
            elif 24 <= program <= 31:
                role = 'guitar'
            elif 32 <= program <= 39:
                role = 'bass'
            elif 40 <= program <= 47:
                role = 'strings'
            elif 112 <= program <= 119:
                role = 'drums'
        mapping[tid] = role
    return mapping


class TrackMapper:
    """类化音轨映射器，支持加载配置与自定义规则。"""
    MAPPING_RULES: Dict[str, str] = {
        r'.*vocal.*|.*voice.*': 'vocals',
        r'.*melody.*|.*lead.*': 'melody',
        r'.*bass.*': 'bass',
        r'.*drum.*|.*percussion.*': 'drums',
        r'.*chord.*|.*pad.*': 'harmony',
    }

    def __init__(self, rules: Optional[List[Tuple[str, str]]] = None, config_path: Optional[str] = None) -> None:
        """Initialize TrackMapper with rules or config file.

        Args:
            rules: Optional list of (pattern, target) tuples
            config_path: Optional path to YAML config file

        Raises:
            ValidationError: If config_path is invalid
        """
        if config_path is not None:
            validate_config_path(config_path)

        # 优先使用传入的 rules（列表 of (pattern,target)），其次尝试从 config_path 或默认 MAPPING_RULES
        if rules is not None:
            self.rules: List[Tuple[str, str]] = rules
        else:
            # 如果没有指定 config_path，尝试加载默认的 mapping_rules.yaml
            if config_path is None:
                default_config = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'mapping_rules.yaml')
                if os.path.exists(default_config):
                    config_path = default_config

            # 尝试从配置文件加载
            if config_path:
                try:
                    import yaml
                    with open(config_path, 'r', encoding='utf-8') as f:
                        doc: Optional[Dict[str, Any]] = yaml.safe_load(f)
                        items: List[Tuple[str, str]] = []
                        for pat, tgt in (doc or {}).items():
                            items.append((pat, tgt))
                        self.rules = items if items else DEFAULT_RULES
                except Exception:
                    self.rules = DEFAULT_RULES
            else:
                # 如果没有配置文件，使用类定义的 MAPPING_RULES
                self.rules = [(k, v) for k, v in self.MAPPING_RULES.items()]

    def auto_map_tracks(self, track_names: Optional[List[str]] = None, events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """自动映射：可传入 track_names（优先）或 events（parse_midi 输出）。返回 {track_name: role} 或 {track_id: role}。

        Args:
            track_names: Optional list of track names
            events: Optional list of note events from parser

        Returns:
            Dictionary mapping track identifiers to roles

        Raises:
            ValidationError: If both track_names and events are None
        """
        if track_names is None and events is None:
            raise ValidationError("Either track_names or events must be provided")

        if track_names is None and events is not None:
            # 尝试从 events 提取 track_name -> use earliest non-null name per track id
            track_names = []
            seen: Dict[int, str] = {}
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                tid: int = ev.get('track', 0)
                name: Optional[str] = ev.get('track_name')
                if tid not in seen and name:
                    seen[tid] = name
            # fallback to track_{id}
            max_tid: int = max((ev.get('track', 0) for ev in events if isinstance(ev, dict)), default=-1)
            track_names = [seen.get(i, f"track_{i}") for i in range(max_tid+1)]

        # now map names
        compiled: List[Tuple[re.Pattern[str], str]] = [(re.compile(pat, re.IGNORECASE), target) for pat, target in self.rules]
        mapping: Dict[str, str] = {}
        for name in (track_names or []):
            assigned: str = 'unknown'
            for cre, target in compiled:
                if cre.search(name or ''):
                    assigned = target
                    break
            mapping[name] = assigned
        return mapping

    def create_custom_mapping(self, user_rules: Dict[str, str]) -> None:
        """用用户规则替换当前规则（user_rules: pattern->target）。

        Args:
            user_rules: Dictionary mapping regex patterns to target roles

        Raises:
            ValidationError: If user_rules is invalid
        """
        validate_track_mapping(user_rules)
        self.rules = [(k, v) for k, v in user_rules.items()]
