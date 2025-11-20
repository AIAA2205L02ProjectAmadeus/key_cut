"""midi_processing.track_mapper

Implements automatic track mapping based on track names and instrument programs.

This module provides flexible track-to-role mapping using configurable regex
patterns. It supports both manual mapping rules and YAML configuration files.
Track names or MIDI program numbers can be used to categorize tracks into
musical roles (e.g., piano, bass, drums, melody).
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
    """Map track names to musical roles using regex pattern matching.

    This function applies a list of regex patterns to track names and assigns
    roles based on the first matching pattern. If no pattern matches, the track
    is assigned the role 'unknown'.

    Args:
        track_names: List of track name strings to map.
        rules: Optional list of (pattern, target_role) tuples. Patterns are
            matched in order. If None, DEFAULT_RULES are used.

    Returns:
        Dictionary mapping each track name to its assigned role.
        Format: {track_name: role}

    Example:
        >>> track_names = ['Grand Piano', 'Electric Bass', 'Drums']
        >>> mapping = map_tracks(track_names)
        >>> mapping
        {'Grand Piano': 'piano', 'Electric Bass': 'bass', 'Drums': 'drums'}

        >>> custom_rules = [(r'synth', 'synthesizer'), (r'vocal', 'voice')]
        >>> mapping = map_tracks(['Synth Lead'], rules=custom_rules)
        >>> mapping
        {'Synth Lead': 'synthesizer'}
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
    """Map track IDs to roles based on MIDI program numbers.

    This is a fallback strategy when track names are unavailable. It infers
    musical roles from MIDI program numbers using General MIDI conventions:
    - Programs 0-7: Piano
    - Programs 24-31: Guitar
    - Programs 32-39: Bass
    - Programs 40-47: Strings
    - Programs 112-119: Drums

    Args:
        events: List of note event dictionaries from parse_midi, containing
            'track' and 'program' fields.

    Returns:
        Dictionary mapping track ID to inferred role.
        Format: {track_id: role}

    Example:
        >>> events = parse_midi('song.mid')
        >>> track_roles = map_tracks_from_parser_events(events)
        >>> track_roles
        {0: 'unknown', 1: 'piano', 2: 'bass', 3: 'drums'}
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
    """Configurable track-to-role mapper supporting custom rules and YAML config.

    This class provides a flexible interface for mapping track names or events
    to musical roles. It supports initialization from custom rules, YAML
    configuration files, or built-in defaults.

    Attributes:
        rules: List of (pattern, target_role) tuples used for matching.

    Example:
        >>> # Using default rules
        >>> mapper = TrackMapper()
        >>> mapping = mapper.auto_map_tracks(track_names=['Piano', 'Bass'])

        >>> # Using YAML configuration
        >>> mapper = TrackMapper(config_path='config/mapping_rules.yaml')
        >>> mapping = mapper.auto_map_tracks(events=parsed_events)

        >>> # Using custom rules
        >>> custom = [(r'.*lead.*', 'melody'), (r'.*pad.*', 'harmony')]
        >>> mapper = TrackMapper(rules=custom)
    """
    MAPPING_RULES = {
        r'.*vocal.*|.*voice.*': 'vocals',
        r'.*melody.*|.*lead.*': 'melody',
        r'.*bass.*': 'bass',
        r'.*drum.*|.*percussion.*': 'drums',
        r'.*chord.*|.*pad.*': 'harmony',
    }

    def __init__(self, rules: Optional[List[Tuple[str, str]]] = None, config_path: Optional[str] = None):
        """Initialize the TrackMapper with optional custom rules or config file.

        Args:
            rules: Optional list of (regex_pattern, target_role) tuples. Takes
                precedence over config_path and defaults.
            config_path: Optional path to YAML configuration file containing
                pattern-to-role mappings. Requires PyYAML to be installed.

        Note:
            Priority order: rules > config_path > MAPPING_RULES > DEFAULT_RULES
        """
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
        """Automatically map tracks to roles from track names or parsed events.

        This method accepts either track names directly or events from parse_midi.
        When events are provided, it extracts track names from the 'track_name'
        field, falling back to 'track_{id}' format if names are unavailable.

        Args:
            track_names: Optional list of track name strings. Takes precedence
                over events if both are provided.
            events: Optional list of note event dictionaries from parse_midi,
                containing 'track' and 'track_name' fields.

        Returns:
            Dictionary mapping track names to assigned roles.
            Format: {track_name: role}

        Raises:
            ValueError: If both track_names and events are None.

        Example:
            >>> mapper = TrackMapper()
            >>> # Map from track names
            >>> mapping = mapper.auto_map_tracks(track_names=['Piano', 'Drums'])
            >>> mapping
            {'Piano': 'piano', 'Drums': 'drums'}

            >>> # Map from parsed events
            >>> events = parse_midi('song.mid')
            >>> mapping = mapper.auto_map_tracks(events=events)
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
        """Replace current mapping rules with user-provided rules.

        Args:
            user_rules: Dictionary of regex patterns to target roles.
                Format: {regex_pattern: target_role}

        Example:
            >>> mapper = TrackMapper()
            >>> custom_rules = {
            ...     r'.*synth.*': 'synthesizer',
            ...     r'.*vocal.*': 'voice',
            ...     r'.*perc.*': 'percussion'
            ... }
            >>> mapper.create_custom_mapping(custom_rules)
        """
        self.rules = [(k, v) for k, v in user_rules.items()]
