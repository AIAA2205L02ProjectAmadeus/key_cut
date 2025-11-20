# Configuration Documentation

This document explains all configuration options available in the MIDI Processing library.

## Table of Contents

- [Configuration Files](#configuration-files)
- [Mapping Rules Configuration](#mapping-rules-configuration)
- [Analysis Configuration](#analysis-configuration)
- [Programmatic Configuration](#programmatic-configuration)

---

## Configuration Files

The library uses YAML configuration files stored in the `config/` directory:

```
config/
├── mapping_rules.yaml    # Track name to role mapping rules
└── analysis_config.yaml  # Analysis parameters
```

### File Format

Configuration files use YAML format. Make sure to:
- Use proper YAML syntax
- Maintain correct indentation (2 spaces recommended)
- Use quotes for regex patterns containing special characters
- Install PyYAML: `pip install pyyaml`

---

## Mapping Rules Configuration

**File:** `config/mapping_rules.yaml`

This file defines regex patterns to map track names to musical roles.

### Format

```yaml
'pattern': role_name
'another_pattern': another_role
```

### Default Configuration

```yaml
# mapping_rules.yaml
# pattern: role
'.*vocal.*|.*voice.*': vocals
'.*melody.*|.*lead.*': melody
'.*bass.*': bass
'.*drum.*|.*percussion.*': drums
'.*chord.*|.*pad.*': harmony
'piano|grand': piano
'guitar': guitar
'bass': bass
'violin|cello|strings': strings
'flute|sax|clarinet': winds
```

### Pattern Syntax

Patterns use Python regular expressions (case-insensitive by default):

- `.` - Matches any character
- `*` - Matches zero or more of the preceding character
- `.*` - Matches any sequence of characters
- `|` - OR operator
- `^` - Start of string
- `$` - End of string
- `[abc]` - Character class (matches a, b, or c)
- `\d` - Matches any digit
- `\w` - Matches any word character

### Pattern Examples

#### Exact Match
```yaml
'piano': piano
'guitar': guitar
```
Matches track names "piano" or "guitar" exactly (case-insensitive).

#### Partial Match
```yaml
'.*bass.*': bass
'.*drum.*': drums
```
Matches any track name containing "bass" or "drum" anywhere.

#### Multiple Alternatives
```yaml
'.*vocal.*|.*voice.*|.*singer.*': vocals
'piano|grand|keys': piano
```
Matches any of the alternatives separated by `|`.

#### Start/End Anchors
```yaml
'^piano.*': piano
'.*lead$': melody
```
- `^piano.*` matches names starting with "piano"
- `.*lead$` matches names ending with "lead"

#### Complex Patterns
```yaml
'.*synth.*(lead|pad).*': synthesizer
'(acoustic|electric).*guitar': guitar
```

### Custom Roles

You can define any role names that make sense for your application:

```yaml
# Custom roles example
'.*melody.*': main_melody
'.*counter.*': counter_melody
'.*synth.*pad.*': atmospheric
'.*arpeggio.*': arpeggiated
'.*fx.*|.*effect.*': sound_effects
```

### Pattern Matching Priority

Patterns are evaluated in order from **top to bottom**. The **first** matching pattern wins.

Example:
```yaml
'.*bass.*drum.*': drums  # Matches first for "bass drum"
'.*bass.*': bass         # Won't match "bass drum" (already matched above)
```

To prioritize specific patterns, place them earlier in the file:
```yaml
# High priority patterns first
'acoustic.*bass': acoustic_bass
'electric.*bass': electric_bass
'.*bass.*': bass  # Fallback for other bass instruments
```

### Usage in Code

#### Load from YAML file
```python
from midi_processing import TrackMapper

mapper = TrackMapper(config_path='config/mapping_rules.yaml')
mapping = mapper.auto_map_tracks(track_names=['Piano Left', 'Bass Guitar'])
```

#### Programmatic configuration
```python
custom_rules = [
    (r'.*synth.*', 'synthesizer'),
    (r'.*vocal.*', 'voice'),
    (r'.*drum.*', 'percussion')
]
mapper = TrackMapper(rules=custom_rules)
```

---

## Analysis Configuration

**File:** `config/analysis_config.yaml`

This file contains parameters for music theory analysis algorithms.

### Format

```yaml
parameter_name: value
another_parameter: value
```

### Default Configuration

```yaml
# analysis_config.yaml
chord_window: 0.5      # Window size for chord detection (seconds)
quantize: 0.125        # Quantization grid size (seconds)
rhythm_top_k: 5        # Number of top rhythm patterns to return
```

### Parameters

#### `chord_window`

**Type:** Float (seconds)
**Default:** 0.5
**Range:** 0.1 - 2.0 (recommended)

Window size for chord detection. Notes within this time window are considered simultaneous and analyzed together.

**Guidelines:**
- **Slow music (ballads, ambient):** 0.75 - 1.5 seconds
- **Medium tempo (pop, rock):** 0.4 - 0.8 seconds
- **Fast music (uptempo, classical):** 0.2 - 0.5 seconds

**Example:**
```yaml
chord_window: 0.75  # Good for slow ballads
```

**Usage in code:**
```python
from midi_processing import analyze_chords, parse_midi

events = parse_midi('song.mid')
# Use custom window
chords = analyze_chords(events, window=0.75)
```

#### `quantize`

**Type:** Float (seconds)
**Default:** 0.125
**Range:** 0.0625 - 0.5 (recommended)

Quantization grid size for note alignment. Notes are snapped to the nearest grid point.

**Common Values (at 120 BPM):**
- `0.5` - Quarter note (4 grids per measure in 4/4)
- `0.25` - Eighth note (8 grids per measure)
- `0.125` - Sixteenth note (16 grids per measure)
- `0.0625` - Thirty-second note (32 grids per measure)

**Tempo Adjustment:**

If your music is at a different tempo, adjust accordingly:
- At 60 BPM (half speed): double the values (0.25 → 0.5)
- At 240 BPM (double speed): halve the values (0.125 → 0.0625)

**Formula:**
```
quantize_seconds = (60 / BPM) / note_division
```

Where note_division is:
- 1 for quarter notes
- 2 for eighth notes
- 4 for sixteenth notes
- 8 for thirty-second notes

**Example:**
```yaml
quantize: 0.0625  # Thirty-second note at 120 BPM
```

**Usage in code:**
```python
from midi_processing import align_notes, parse_midi

events = parse_midi('song.mid')
# Use custom quantization
aligned = align_notes(events, quantize=0.0625)
```

#### `rhythm_top_k`

**Type:** Integer
**Default:** 5
**Range:** 1 - 20

Number of most common rhythm patterns (inter-onset intervals) to return from rhythm analysis.

**Guidelines:**
- **Simple rhythm:** 3-5
- **Complex rhythm:** 5-10
- **Detailed analysis:** 10-20

**Example:**
```yaml
rhythm_top_k: 10  # Return top 10 patterns
```

**Usage in code:**
```python
from midi_processing import rhythm_pattern, parse_midi

events = parse_midi('song.mid')
# Get top 10 patterns
patterns = rhythm_pattern(events, top_k=10)
```

---

## Programmatic Configuration

You can override configuration values directly in your code without modifying files.

### TrackMapper Configuration

```python
from midi_processing import TrackMapper

# Option 1: Custom rules as list of tuples
custom_rules = [
    (r'.*piano.*', 'piano'),
    (r'.*synth.*', 'synthesizer'),
    (r'.*drum.*', 'percussion')
]
mapper = TrackMapper(rules=custom_rules)

# Option 2: From YAML file
mapper = TrackMapper(config_path='config/custom_mapping.yaml')

# Option 3: Update rules dynamically
mapper = TrackMapper()
new_rules = {
    r'.*lead.*': 'melody',
    r'.*pad.*': 'harmony'
}
mapper.create_custom_mapping(new_rules)
```

### Analysis Parameters

```python
from midi_processing import analyze_chords, align_notes, rhythm_pattern

# Override chord_window
chords = analyze_chords(events, window=0.75)

# Override quantize
aligned = align_notes(events, quantize=0.0625)

# Override rhythm_top_k
patterns = rhythm_pattern(events, top_k=10)
```

### MusicTimeline Configuration

```python
from midi_processing import MusicTimeline

# Set quantization at initialization
timeline = MusicTimeline(quantize=0.25)
aligned = timeline.align_notes(events)

# Different quantization for different timelines
coarse_timeline = MusicTimeline(quantize=0.5)
fine_timeline = MusicTimeline(quantize=0.0625)
```

---

## Configuration Best Practices

### 1. Start with Defaults

Begin with default configuration and adjust only when needed:
```python
# Use defaults
mapper = TrackMapper()
timeline = MusicTimeline()
```

### 2. Experiment with Parameters

Try different values to find what works best for your specific MIDI files:

```python
# Test different chord windows
for window in [0.25, 0.5, 0.75, 1.0]:
    chords = analyze_chords(events, window=window)
    print(f"Window {window}s: {len(chords)} chords detected")
```

### 3. Document Custom Configurations

When using custom configurations, document your choices:

```yaml
# mapping_rules.yaml
# Custom mapping for orchestral scores
# Priority: specific instruments -> sections -> generic fallback

'.*solo.*violin.*': solo_violin
'.*violin.*': violin_section
'.*strings.*': string_section
'.*orchestra.*': full_orchestra
```

### 4. Version Control Configuration Files

Keep configuration files in version control alongside your code:

```bash
git add config/mapping_rules.yaml config/analysis_config.yaml
git commit -m "Add custom MIDI analysis configuration"
```

### 5. Validate YAML Syntax

Ensure your YAML files are valid before using them:

```python
import yaml

try:
    with open('config/mapping_rules.yaml') as f:
        config = yaml.safe_load(f)
    print("Configuration is valid!")
except yaml.YAMLError as e:
    print(f"Configuration error: {e}")
```

---

## Troubleshooting Configuration

### Issue: Track not being mapped correctly

**Solution:** Check pattern matching order and regex syntax.

```python
# Debug mapping
mapper = TrackMapper(config_path='config/mapping_rules.yaml')
print(mapper.rules)  # View loaded rules

# Test individual track names
mapping = mapper.auto_map_tracks(track_names=['Synth Lead'])
print(mapping)
```

### Issue: YAML file not loading

**Solution:** Ensure PyYAML is installed and file path is correct.

```bash
pip install pyyaml
```

```python
import os
print(os.path.exists('config/mapping_rules.yaml'))  # Should print True
```

### Issue: Analysis produces unexpected results

**Solution:** Adjust parameters based on your music's characteristics.

```python
# For slow music, try larger chord window
chords = analyze_chords(events, window=1.0)

# For faster quantization, use smaller grid
aligned = align_notes(events, quantize=0.0625)
```

---

## Example Configurations

### Jazz/Complex Harmony
```yaml
# mapping_rules.yaml
'.*piano.*|.*keys.*': piano
'.*bass.*': bass
'.*drum.*|.*kit.*': drums
'.*sax.*|.*trumpet.*|.*trombone.*': horns
'.*guitar.*': guitar

# analysis_config.yaml
chord_window: 0.4      # Fast chord changes
quantize: 0.083        # Triplet feel (1/12 of a beat at 120 BPM)
rhythm_top_k: 10       # Complex rhythms
```

### Electronic/EDM
```yaml
# mapping_rules.yaml
'.*kick.*': kick
'.*bass.*': bass
'.*lead.*|.*melody.*': lead_synth
'.*pad.*|.*chord.*': pad
'.*perc.*|.*drum.*': drums
'.*fx.*|.*effect.*': effects

# analysis_config.yaml
chord_window: 0.5
quantize: 0.125        # Standard 16th note grid
rhythm_top_k: 5
```

### Classical/Orchestral
```yaml
# mapping_rules.yaml
'.*violin.*': violins
'.*viola.*': violas
'.*cello.*': cellos
'.*bass.*': double_bass
'.*flute.*': flutes
'.*oboe.*': oboes
'.*clarinet.*': clarinets
'.*horn.*': horns
'.*trumpet.*': trumpets
'.*trombone.*': trombones
'.*timpani.*': timpani

# analysis_config.yaml
chord_window: 0.75     # Slower, longer phrases
quantize: 0.125
rhythm_top_k: 8
```
