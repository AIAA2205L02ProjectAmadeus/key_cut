"""midi_processing.track_mapper

Implements automatic track mapping based on track names and instrument programs.

This module provides flexible track-to-role mapping using configurable regex
patterns. It supports both manual mapping rules and YAML configuration files.
Track names or MIDI program numbers can be used to categorize tracks into
musical roles (e.g., piano, bass, drums, melody).
"""
from typing import List, Dict, Tuple, Optional
import re
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
            # 如果没有指定 config_path，尝试加载默认的 mapping_rules.yaml
            if config_path is None:
                default_config = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'mapping_rules.yaml')
                if os.path.exists(default_config):
                    config_path = default_config

            # 尝试从配置文件加载
            if config_path:
                try:
                    import yaml
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            doc = yaml.safe_load(f)
                    except FileNotFoundError:
                        raise ConfigurationError(
                            f"Configuration file not found. Please ensure the file exists at the specified path.",
                            config_path=config_path
                        )
                    except PermissionError as e:
                        raise ConfigurationError(
                            f"Permission denied when reading configuration file.",
                            config_path=config_path,
                            original_error=e
                        )
                    except yaml.YAMLError as e:
                        raise ConfigurationError(
                            f"Invalid YAML format in configuration file. Please check the file syntax.",
                            config_path=config_path,
                            original_error=e
                        )
                    except Exception as e:
                        raise ConfigurationError(
                            f"Failed to read configuration file.",
                            config_path=config_path,
                            original_error=e
                        )

                    # Validate loaded configuration
                    if doc is None:
                        raise ConfigurationError(
                            f"Configuration file is empty or contains only null values.",
                            config_path=config_path
                        )

                    if not isinstance(doc, dict):
                        raise ConfigurationError(
                            f"Configuration must be a YAML dictionary (key-value pairs), not {type(doc).__name__}.",
                            config_path=config_path
                        )

                    items = []
                    for pat, tgt in doc.items():
                        if not isinstance(pat, str):
                            raise ConfigurationError(
                                f"Configuration pattern keys must be strings, found {type(pat).__name__}.",
                                config_path=config_path
                            )
                        if not isinstance(tgt, str):
                            raise ConfigurationError(
                                f"Configuration target values must be strings, found {type(tgt).__name__} for pattern '{pat}'.",
                                config_path=config_path
                            )
                        # Validate regex pattern
                        try:
                            re.compile(pat, re.IGNORECASE)
                        except re.error as e:
                            raise ConfigurationError(
                                f"Invalid regex pattern '{pat}' in configuration.",
                                config_path=config_path,
                                original_error=e
                            )
                        items.append((pat, tgt))
                    self.rules = items if items else DEFAULT_RULES
                except ConfigurationError:
                    raise  # Re-raise our custom configuration errors
                except ImportError:
                    raise ConfigurationError(
                        "YAML library (pyyaml) is not installed. Please install it to use YAML configuration files: pip install pyyaml",
                        config_path=config_path
                    )
            else:
                # 如果没有配置文件，使用类定义的 MAPPING_RULES
                self.rules = [(k, v) for k, v in self.MAPPING_RULES.items()]

    def _load_rules_from_yaml(self, config_path: str) -> List[Tuple[str, str]]:
        """从 YAML 文件加载映射规则，失败时回退到 DEFAULT_RULES。

        参数:
          - config_path: YAML 配置文件路径

        返回:
          - 规则列表 [(pattern, target), ...]
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                doc = yaml.safe_load(f)
                if not doc or not isinstance(doc, dict):
                    # 文件为空或格式不正确，使用默认规则
                    return DEFAULT_RULES

                items = []
                for pat, tgt in doc.items():
                    if isinstance(pat, str) and isinstance(tgt, str):
                        items.append((pat, tgt))

                # 如果成功加载了至少一条规则，使用加载的规则；否则使用默认规则
                return items if items else DEFAULT_RULES
        except (FileNotFoundError, IOError, yaml.YAMLError) as e:
            # 文件不存在、读取错误或 YAML 解析错误，回退到默认规则
            return DEFAULT_RULES
        except Exception as e:
            # 其他未预期的错误，也回退到默认规则
            return DEFAULT_RULES

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
