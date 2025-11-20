# API Reference

Complete API documentation for the MIDI Processing library.

## Table of Contents

- [midi_parser Module](#midi_parser-module)
- [track_mapper Module](#track_mapper-module)
- [music_analyzer Module](#music_analyzer-module)
- [timeline_generator Module](#timeline_generator-module)

---

## midi_parser Module

The `midi_parser` module provides low-level MIDI file parsing functionality.

### Functions

#### `parse_midi(path: str) -> List[Dict[str, Any]]`

Parse a MIDI file and return a list of note events.

**Parameters:**
- `path` (str): File path to the MIDI file to parse.

**Returns:**
- List of note event dictionaries, each containing:
  - `note` (int): MIDI note number (0-127)
  - `velocity` (int): Note velocity (1-127)
  - `start` (float): Note start time in seconds
  - `end` (float): Note end time in seconds
  - `channel` (int): MIDI channel (0-15)
  - `track` (int): Track index in the MIDI file
  - `track_name` (str or None): Name of the track (if available)
  - `program` (int): MIDI program/instrument number (-1 if not set)

**Example:**
```python
from midi_processing import parse_midi

events = parse_midi('song.mid')
print(f"Found {len(events)} note events")
print(f"First note: {events[0]['note']} at {events[0]['start']}s")
```

**Notes:**
- Events are sorted by start time
- Tempo changes are automatically handled
- All timing is in seconds (float)

---

### Classes

#### `AdvancedMIDIParser`

Advanced MIDI parser providing a class-based API with additional utilities.

##### `__init__()`

Initialize the AdvancedMIDIParser.

**Example:**
```python
from midi_processing import AdvancedMIDIParser

parser = AdvancedMIDIParser()
```

##### `parse_midi_file(file_path: str) -> List[Dict[str, Any]]`

Parse a MIDI file and return note events (same format as `parse_midi`).

**Parameters:**
- `file_path` (str): Path to the MIDI file.

**Returns:**
- List of note event dictionaries.

**Example:**
```python
parser = AdvancedMIDIParser()
events = parser.parse_midi_file('example.mid')
```

##### `extract_note_events(midi_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Filter and return only note events from parsed MIDI events.

**Parameters:**
- `midi_events` (list): List of MIDI events from `parse_midi`.

**Returns:**
- Filtered list of note events, sorted by start time.

**Note:** This is primarily for compatibility, as `parse_midi` already returns only note events.

##### `detect_tracks(file_path: str) -> List[Dict[str, Any]]`

Detect and return metadata for each track in a MIDI file.

**Parameters:**
- `file_path` (str): Path to the MIDI file.

**Returns:**
- List of track metadata dictionaries, each containing:
  - `track_id` (int): Zero-based track index
  - `track_name` (str or None): Track name from meta message
  - `programs` (list): Sorted list of program numbers used in the track

**Example:**
```python
parser = AdvancedMIDIParser()
tracks = parser.detect_tracks('song.mid')
for track in tracks:
    print(f"Track {track['track_id']}: {track['track_name']}")
    print(f"  Programs: {track['programs']}")
```

---

## track_mapper Module

The `track_mapper` module provides automatic track-to-role mapping based on track names or instrument programs.

### Constants

#### `DEFAULT_RULES`

Default regex pattern rules for track mapping:
```python
DEFAULT_RULES = [
    (r'piano|grand', 'piano'),
    (r'guitar', 'guitar'),
    (r'bass', 'bass'),
    (r'drum|perc', 'drums'),
    (r'violin|cello|strings', 'strings'),
    (r'flute|sax|clarinet', 'winds'),
]
```

### Functions

#### `map_tracks(track_names: List[str], rules: Optional[List[Tuple[str, str]]] = None) -> Dict[str, str]`

Map track names to musical roles using regex pattern matching.

**Parameters:**
- `track_names` (list): List of track name strings to map.
- `rules` (list, optional): List of (pattern, target_role) tuples. If None, `DEFAULT_RULES` are used.

**Returns:**
- Dictionary mapping each track name to its assigned role: `{track_name: role}`

**Example:**
```python
from midi_processing import map_tracks

track_names = ['Grand Piano', 'Electric Bass', 'Drums']
mapping = map_tracks(track_names)
# {'Grand Piano': 'piano', 'Electric Bass': 'bass', 'Drums': 'drums'}

# With custom rules
custom_rules = [(r'synth', 'synthesizer'), (r'vocal', 'voice')]
mapping = map_tracks(['Synth Lead'], rules=custom_rules)
```

#### `map_tracks_from_parser_events(events: List[Dict]) -> Dict[int, str]`

Map track IDs to roles based on MIDI program numbers (fallback strategy).

**Parameters:**
- `events` (list): List of note event dictionaries from `parse_midi`.

**Returns:**
- Dictionary mapping track ID to inferred role: `{track_id: role}`

**Program Number Mapping:**
- Programs 0-7: Piano
- Programs 24-31: Guitar
- Programs 32-39: Bass
- Programs 40-47: Strings
- Programs 112-119: Drums

**Example:**
```python
from midi_processing import parse_midi, map_tracks_from_parser_events

events = parse_midi('song.mid')
track_roles = map_tracks_from_parser_events(events)
```

---

### Classes

#### `TrackMapper`

Configurable track-to-role mapper supporting custom rules and YAML configuration.

##### `__init__(rules: Optional[List[Tuple[str, str]]] = None, config_path: Optional[str] = None)`

Initialize the TrackMapper.

**Parameters:**
- `rules` (list, optional): List of (regex_pattern, target_role) tuples.
- `config_path` (str, optional): Path to YAML configuration file.

**Priority:** rules > config_path > MAPPING_RULES > DEFAULT_RULES

**Example:**
```python
from midi_processing import TrackMapper

# Using default rules
mapper = TrackMapper()

# Using YAML configuration
mapper = TrackMapper(config_path='config/mapping_rules.yaml')

# Using custom rules
custom = [(r'.*lead.*', 'melody'), (r'.*pad.*', 'harmony')]
mapper = TrackMapper(rules=custom)
```

##### `auto_map_tracks(track_names: Optional[List[str]] = None, events: Optional[List[Dict]] = None) -> Dict[str, str]`

Automatically map tracks to roles from track names or parsed events.

**Parameters:**
- `track_names` (list, optional): List of track name strings.
- `events` (list, optional): List of note event dictionaries.

**Returns:**
- Dictionary mapping track names to assigned roles.

**Example:**
```python
mapper = TrackMapper()

# Map from track names
mapping = mapper.auto_map_tracks(track_names=['Piano', 'Drums'])

# Map from parsed events
events = parse_midi('song.mid')
mapping = mapper.auto_map_tracks(events=events)
```

##### `create_custom_mapping(user_rules: Dict[str, str])`

Replace current mapping rules with user-provided rules.

**Parameters:**
- `user_rules` (dict): Dictionary of regex patterns to target roles.

**Example:**
```python
mapper = TrackMapper()
custom_rules = {
    r'.*synth.*': 'synthesizer',
    r'.*vocal.*': 'voice',
    r'.*perc.*': 'percussion'
}
mapper.create_custom_mapping(custom_rules)
```

---

## music_analyzer Module

The `music_analyzer` module provides music theory analysis functionality.

### Constants

#### `KRUMHANSL_MAJOR` and `KRUMHANSL_MINOR`

Krumhansl-Schmuckler key profiles used for key detection.

#### `NOTE_NAMES`

List of note names: `['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']`

### Functions

#### `detect_key(events: List[Dict]) -> str`

Detect the musical key using the Krumhansl-Schmuckler algorithm.

**Parameters:**
- `events` (list): List of note event dictionaries.

**Returns:**
- String representing the detected key (e.g., 'C major', 'A minor', or 'Unknown').

**Example:**
```python
from midi_processing import parse_midi, detect_key

events = parse_midi('song.mid')
key = detect_key(events)
print(f"Detected key: {key}")
```

**Algorithm:**
- Calculates pitch class distribution weighted by note duration
- Correlates with Krumhansl's key profiles for all 24 keys
- Returns the key with highest correlation

#### `analyze_chords(events: List[Dict], window: float = 0.5) -> List[Dict]`

Identify chords using window-based pitch class analysis.

**Parameters:**
- `events` (list): List of note event dictionaries.
- `window` (float): Time window size in seconds. Default is 0.5.

**Returns:**
- List of chord dictionaries, each containing:
  - `time` (float): Start time of the chord
  - `root` (str or None): Root note name
  - `type` (str): Chord type ('major', 'minor', 'diminished', 'cluster')
  - `notes` (list): Pitch classes (0-11) present

**Example:**
```python
from midi_processing import parse_midi, analyze_chords

events = parse_midi('chord_progression.mid')
chords = analyze_chords(events, window=0.5)
for chord in chords[:5]:
    print(f"{chord['time']:.2f}s: {chord['root']} {chord['type']}")
```

**Recognized Triads:**
- Major: root + major 3rd + perfect 5th (intervals 0, 4, 7)
- Minor: root + minor 3rd + perfect 5th (intervals 0, 3, 7)
- Diminished: root + minor 3rd + diminished 5th (intervals 0, 3, 6)

#### `rhythm_pattern(events: List[Dict], top_k: int = 5) -> List[Tuple[float, int]]`

Analyze rhythm patterns using inter-onset interval (IOI) histogram.

**Parameters:**
- `events` (list): List of note event dictionaries.
- `top_k` (int): Number of most common intervals to return. Default is 5.

**Returns:**
- List of (interval, count) tuples, sorted by frequency.

**Example:**
```python
from midi_processing import parse_midi, rhythm_pattern

events = parse_midi('rhythmic_piece.mid')
patterns = rhythm_pattern(events, top_k=5)
for interval, count in patterns:
    print(f"Interval: {interval}s, Count: {count}")
```

**Interpretation (at 120 BPM):**
- 0.5s = quarter note
- 0.25s = eighth note
- 0.125s = sixteenth note

#### `align_notes(events: List[Dict], quantize: float = 0.125) -> List[Dict]`

Quantize note timings to a rhythmic grid and merge overlapping notes.

**Parameters:**
- `events` (list): List of note event dictionaries.
- `quantize` (float): Grid spacing in seconds. Default is 0.125.

**Returns:**
- New list of quantized event dictionaries.

**Example:**
```python
from midi_processing import parse_midi, align_notes

events = parse_midi('slightly_off_timing.mid')
aligned = align_notes(events, quantize=0.125)
```

**Common Quantize Values (at 120 BPM):**
- 0.5 = quarter note
- 0.25 = eighth note
- 0.125 = sixteenth note
- 0.0625 = thirty-second note

---

## timeline_generator Module

The `timeline_generator` module provides timeline generation and sequencing utilities.

### Classes

#### `MusicTimeline`

Timeline generator for aligning and sequencing musical events.

##### `__init__(quantize: float = 0.125)`

Initialize the MusicTimeline.

**Parameters:**
- `quantize` (float): Grid spacing in seconds. Default is 0.125.

**Example:**
```python
from midi_processing import MusicTimeline

timeline = MusicTimeline(quantize=0.125)
```

##### `align_notes(notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Quantize and merge overlapping notes.

**Parameters:**
- `notes` (list): List of note event dictionaries.

**Returns:**
- List of quantized and merged note events.

**Example:**
```python
timeline = MusicTimeline(quantize=0.25)
aligned = timeline.align_notes(events)
```

##### `handle_overlap(notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Alias for `align_notes`.

##### `generate_sequence(mapped_tracks: Dict) -> List[Dict[str, Any]]`

Generate a chronological sequence from mapped track events.

**Parameters:**
- `mapped_tracks` (dict): Dictionary mapping roles to event lists. Format: `{role: [events]}`

**Returns:**
- Single merged list of events sorted by start time, with 'role' field added.

**Example:**
```python
from midi_processing import parse_midi, TrackMapper, MusicTimeline

# Parse and map tracks
events = parse_midi('song.mid')
mapper = TrackMapper()
mapping = mapper.auto_map_tracks(events=events)

# Group events by role
mapped_tracks = {}
for ev in events:
    role = mapping.get(ev.get('track_name', f"track_{ev['track']}"), 'unknown')
    if role not in mapped_tracks:
        mapped_tracks[role] = []
    mapped_tracks[role].append(ev)

# Generate sequence
timeline = MusicTimeline()
sequence = timeline.generate_sequence(mapped_tracks)
print(f"Generated sequence with {len(sequence)} events")
```

---

## Complete Workflow Example

Here's a complete example demonstrating the full API:

```python
from midi_processing import (
    parse_midi,
    detect_key,
    analyze_chords,
    rhythm_pattern,
    TrackMapper,
    MusicTimeline
)

# 1. Parse MIDI file
events = parse_midi('song.mid')
print(f"Parsed {len(events)} note events")

# 2. Analyze key
key = detect_key(events)
print(f"Key: {key}")

# 3. Analyze chords
chords = analyze_chords(events, window=0.5)
print(f"Found {len(chords)} chords")
for chord in chords[:3]:
    print(f"  {chord['time']:.2f}s: {chord['root']} {chord['type']}")

# 4. Analyze rhythm
patterns = rhythm_pattern(events, top_k=3)
print("Top rhythm patterns:")
for interval, count in patterns:
    print(f"  {interval}s: {count} occurrences")

# 5. Map tracks to roles
mapper = TrackMapper(config_path='config/mapping_rules.yaml')
mapping = mapper.auto_map_tracks(events=events)
print(f"Track mapping: {mapping}")

# 6. Create aligned timeline
timeline = MusicTimeline(quantize=0.125)
aligned = timeline.align_notes(events)
print(f"Aligned {len(aligned)} notes")

# 7. Generate sequence with roles
mapped_tracks = {}
for ev in events:
    track_name = ev.get('track_name', f"track_{ev['track']}")
    role = mapping.get(track_name, 'unknown')
    if role not in mapped_tracks:
        mapped_tracks[role] = []
    mapped_tracks[role].append(ev)

sequence = timeline.generate_sequence(mapped_tracks)
print(f"Generated sequence with {len(sequence)} events")
```
