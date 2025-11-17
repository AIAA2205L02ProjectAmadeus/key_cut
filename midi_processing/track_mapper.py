"""midi_processing.track_mapper

实现基于轨道名称的自动映射，支持可配置的正则规则与默认策略。
"""
from typing import List, Dict, Tuple, Optional
import re

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
    """
    rules = rules or DEFAULT_RULES
    compiled = [(re.compile(pat, re.IGNORECASE), target) for pat, target in rules]
    mapping: Dict[str, str] = {}
    for name in track_names:
        assigned = 'unknown'
        for cre, target in compiled:
            if cre.search(name or ''):
                assigned = target
                break
        mapping[name] = assigned
    return mapping


def map_tracks_from_parser_events(events: List[Dict]) -> Dict[int, str]:
    """辅助函数：从解析器事件中基于 track id 提取名字并映射。
    解析器当前只提供 track id，若没有名字则使用 'track_{id}'。
    返回 {track_id: role}
    """
    # 这里我们没有 track 名称信息，因此返回 default roles per program if available
    # 作为后备策略：如果存在 program 字段，按 program 范围推测（简化）
    mapping: Dict[int, str] = {}
    for ev in events:
        tid = ev.get('track', 0)
        if tid in mapping:
            continue
        program = ev.get('program', -1)
        role = 'unknown'
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
    MAPPING_RULES = {
        r'.*vocal.*|.*voice.*': 'vocals',
        r'.*melody.*|.*lead.*': 'melody',
        r'.*bass.*': 'bass',
        r'.*drum.*|.*percussion.*': 'drums',
        r'.*chord.*|.*pad.*': 'harmony',
    }

    def __init__(self, rules: Optional[List[Tuple[str, str]]] = None, config_path: Optional[str] = None):
        # 优先使用传入的 rules（列表 of (pattern,target)），其次尝试从 config_path 或默认 MAPPING_RULES
        if rules is not None:
            self.rules = rules
        else:
            if config_path:
                try:
                    import yaml
                    with open(config_path, 'r', encoding='utf-8') as f:
                        doc = yaml.safe_load(f)
                        items = []
                        for pat, tgt in (doc or {}).items():
                            items.append((pat, tgt))
                        self.rules = items if items else DEFAULT_RULES
                except Exception:
                    self.rules = DEFAULT_RULES
            else:
                # convert MAPPING_RULES dict to list
                self.rules = [(k, v) for k, v in self.MAPPING_RULES.items()]

    def auto_map_tracks(self, track_names: Optional[List[str]] = None, events: Optional[List[Dict]] = None) -> Dict[str, str]:
        """自动映射：可传入 track_names（优先）或 events（parse_midi 输出）。返回 {track_name: role} 或 {track_id: role}。
        """
        if track_names is None and events is not None:
            # 尝试从 events 提取 track_name -> use earliest non-null name per track id
            track_names = []
            seen = {}
            for ev in events:
                tid = ev.get('track', 0)
                name = ev.get('track_name')
                if tid not in seen and name:
                    seen[tid] = name
            # fallback to track_{id}
            max_tid = max((ev.get('track', 0) for ev in events), default=-1)
            track_names = [seen.get(i, f"track_{i}") for i in range(max_tid+1)]

        # now map names
        compiled = [(re.compile(pat, re.IGNORECASE), target) for pat, target in self.rules]
        mapping: Dict[str, str] = {}
        for name in (track_names or []):
            assigned = 'unknown'
            for cre, target in compiled:
                if cre.search(name or ''):
                    assigned = target
                    break
            mapping[name] = assigned
        return mapping

    def create_custom_mapping(self, user_rules: Dict[str, str]):
        """用用户规则替换当前规则（user_rules: pattern->target）。"""
        self.rules = [(k, v) for k, v in user_rules.items()]
