# Usage Examples

Comprehensive code examples demonstrating various use cases of the MIDI Processing library.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Analysis Examples](#analysis-examples)
- [Track Mapping Examples](#track-mapping-examples)
- [Advanced Examples](#advanced-examples)
- [Real-World Scenarios](#real-world-scenarios)

---

## Basic Examples

### Example 1: Parse and Print MIDI Information

```python
from midi_processing import parse_midi

# Parse a MIDI file
events = parse_midi('song.mid')

# Print basic information
print(f"Total events: {len(events)}")
print(f"Duration: {events[-1]['end']:.2f} seconds")
print(f"First event: Note {events[0]['note']} at {events[0]['start']:.2f}s")
print(f"Last event: Note {events[-1]['note']} at {events[-1]['end']:.2f}s")

# Count notes per track
from collections import Counter
track_counts = Counter(ev['track'] for ev in events)
print(f"\nNotes per track:")
for track_id, count in sorted(track_counts.items()):
    print(f"  Track {track_id}: {count} notes")
```

### Example 2: Extract Track Information

```python
from midi_processing import AdvancedMIDIParser

parser = AdvancedMIDIParser()

# Get track metadata
tracks = parser.detect_tracks('song.mid')

print("Track Information:")
for track in tracks:
    track_id = track['track_id']
    track_name = track['track_name'] or '(unnamed)'
    programs = track['programs']

    print(f"\nTrack {track_id}: {track_name}")
    if programs:
        print(f"  Instruments (programs): {programs}")
```

### Example 3: Simple Key Detection

```python
from midi_processing import parse_midi, detect_key

events = parse_midi('song.mid')
key = detect_key(events)

print(f"Detected key: {key}")

# Interpret the result
if 'major' in key.lower():
    print("This piece is in a major key (bright, happy)")
elif 'minor' in key.lower():
    print("This piece is in a minor key (dark, sad)")
else:
    print("Unable to determine key")
```

---

## Analysis Examples

### Example 4: Chord Progression Analysis

```python
from midi_processing import parse_midi, analyze_chords

events = parse_midi('chord_progression.mid')

# Analyze with different window sizes
for window_size in [0.25, 0.5, 1.0]:
    chords = analyze_chords(events, window=window_size)
    print(f"\nWith window={window_size}s: {len(chords)} chords detected")

    # Print first 5 chords
    for i, chord in enumerate(chords[:5], 1):
        time = chord['time']
        root = chord['root'] or '?'
        chord_type = chord['type']
        print(f"  {i}. Time {time:5.2f}s: {root:3s} {chord_type}")
```

### Example 5: Rhythm Pattern Analysis

```python
from midi_processing import parse_midi, rhythm_pattern

events = parse_midi('rhythmic_piece.mid')

# Analyze rhythm patterns
patterns = rhythm_pattern(events, top_k=10)

print("Most common rhythm patterns:")
print(f"{'Rank':<6} {'Interval (s)':<15} {'Count':<10} {'Note Value (120 BPM)':<25}")
print("-" * 66)

# Helper to interpret intervals
def interpret_interval(interval_sec):
    """Interpret interval as musical note value at 120 BPM."""
    beat_duration = 0.5  # Quarter note at 120 BPM
    ratio = interval_sec / beat_duration

    if abs(ratio - 1.0) < 0.05:
        return "Quarter note"
    elif abs(ratio - 0.5) < 0.05:
        return "Eighth note"
    elif abs(ratio - 0.25) < 0.05:
        return "Sixteenth note"
    elif abs(ratio - 2.0) < 0.05:
        return "Half note"
    elif abs(ratio - 0.75) < 0.05:
        return "Dotted eighth"
    elif abs(ratio - 0.333) < 0.05:
        return "Eighth triplet"
    else:
        return f"{ratio:.2f}x quarter note"

for rank, (interval, count) in enumerate(patterns, 1):
    note_value = interpret_interval(interval)
    print(f"{rank:<6} {interval:<15.6f} {count:<10} {note_value:<25}")
```

### Example 6: Note Quantization and Alignment

```python
from midi_processing import parse_midi, align_notes

events = parse_midi('slightly_off_timing.mid')

print(f"Original: {len(events)} events")

# Quantize to different grid sizes
for grid_size in [0.5, 0.25, 0.125]:
    aligned = align_notes(events, quantize=grid_size)
    print(f"\nQuantized to {grid_size}s grid: {len(aligned)} events")

    # Show before/after for first event
    if events:
        orig = events[0]
        quant = aligned[0]
        print(f"  First note timing:")
        print(f"    Original: {orig['start']:.6f}s - {orig['end']:.6f}s")
        print(f"    Quantized: {quant['start']:.6f}s - {quant['end']:.6f}s")
```

---

## Track Mapping Examples

### Example 7: Automatic Track Mapping

```python
from midi_processing import parse_midi, TrackMapper

events = parse_midi('multi_track_song.mid')

# Create mapper with default rules
mapper = TrackMapper()

# Automatically map tracks
mapping = mapper.auto_map_tracks(events=events)

print("Track Mapping Results:")
for track_name, role in mapping.items():
    print(f"  {track_name:20s} -> {role}")

# Count events per role
role_counts = {}
for ev in events:
    track_name = ev.get('track_name', f"track_{ev['track']}")
    role = mapping.get(track_name, 'unknown')
    role_counts[role] = role_counts.get(role, 0) + 1

print("\nEvents per role:")
for role, count in sorted(role_counts.items()):
    print(f"  {role:15s}: {count:5d} events")
```

### Example 8: Custom Mapping Rules

```python
from midi_processing import TrackMapper

# Define custom rules for your specific MIDI files
custom_rules = [
    (r'.*lead.*|.*melody.*', 'main_melody'),
    (r'.*rhythm.*|.*chord.*', 'rhythm_guitar'),
    (r'.*bass.*', 'bass'),
    (r'.*drum.*|.*kit.*', 'drums'),
    (r'.*synth.*pad.*', 'atmospheric_pad'),
    (r'.*arp.*', 'arpeggiated'),
    (r'.*vocal.*|.*voice.*', 'vocals'),
]

mapper = TrackMapper(rules=custom_rules)

track_names = [
    'Lead Synth',
    'Rhythm Guitar',
    'Bass Guitar',
    'Drum Kit',
    'Synth Pad',
    'Vocal Main'
]

mapping = mapper.auto_map_tracks(track_names=track_names)

for name, role in mapping.items():
    print(f"{name:20s} -> {role}")
```

### Example 9: YAML Configuration

```python
from midi_processing import TrackMapper
import yaml

# Load and display YAML config
with open('config/mapping_rules.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print("Loaded mapping rules:")
    for pattern, role in config.items():
        print(f"  {pattern:30s} -> {role}")

# Use the configuration
mapper = TrackMapper(config_path='config/mapping_rules.yaml')
mapping = mapper.auto_map_tracks(track_names=['Grand Piano', 'Electric Bass'])
print(f"\nMapping result: {mapping}")
```

---

## Advanced Examples

### Example 10: Complete Music Analysis Pipeline

```python
from midi_processing import (
    parse_midi,
    detect_key,
    analyze_chords,
    rhythm_pattern,
    TrackMapper,
    MusicTimeline
)

def analyze_midi_file(filepath):
    """Comprehensive analysis of a MIDI file."""

    print(f"Analyzing: {filepath}")
    print("=" * 70)

    # 1. Parse MIDI
    print("\n1. Parsing MIDI file...")
    events = parse_midi(filepath)
    duration = events[-1]['end'] if events else 0
    print(f"   Found {len(events)} note events")
    print(f"   Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")

    # 2. Detect key
    print("\n2. Detecting musical key...")
    key = detect_key(events)
    print(f"   Key: {key}")

    # 3. Analyze chords
    print("\n3. Analyzing chord progression...")
    chords = analyze_chords(events, window=0.5)
    print(f"   Detected {len(chords)} chords")
    print("   First 5 chords:")
    for chord in chords[:5]:
        print(f"      {chord['time']:5.2f}s: {chord['root']} {chord['type']}")

    # 4. Analyze rhythm
    print("\n4. Analyzing rhythm patterns...")
    patterns = rhythm_pattern(events, top_k=5)
    print("   Top 5 rhythm patterns:")
    for i, (interval, count) in enumerate(patterns, 1):
        print(f"      {i}. {interval:.3f}s ({count} occurrences)")

    # 5. Map tracks
    print("\n5. Mapping tracks to roles...")
    mapper = TrackMapper()
    mapping = mapper.auto_map_tracks(events=events)
    print("   Track mapping:")
    for track_name, role in mapping.items():
        print(f"      {track_name:20s} -> {role}")

    # 6. Create timeline
    print("\n6. Creating aligned timeline...")
    timeline = MusicTimeline(quantize=0.125)
    aligned = timeline.align_notes(events)
    print(f"   Aligned {len(aligned)} events (from {len(events)} original)")

    return {
        'events': events,
        'key': key,
        'chords': chords,
        'patterns': patterns,
        'mapping': mapping,
        'aligned': aligned
    }

# Run analysis
results = analyze_midi_file('song.mid')
```

### Example 11: Generate Timeline with Roles

```python
from midi_processing import parse_midi, TrackMapper, MusicTimeline

def create_role_based_timeline(filepath):
    """Create a timeline with events grouped by musical role."""

    # Parse and map
    events = parse_midi(filepath)
    mapper = TrackMapper()
    mapping = mapper.auto_map_tracks(events=events)

    # Group events by role
    mapped_tracks = {}
    for ev in events:
        track_name = ev.get('track_name', f"track_{ev['track']}")
        role = mapping.get(track_name, 'unknown')

        if role not in mapped_tracks:
            mapped_tracks[role] = []
        mapped_tracks[role].append(ev)

    # Create timeline
    timeline = MusicTimeline(quantize=0.125)
    sequence = timeline.generate_sequence(mapped_tracks)

    # Print timeline summary
    print(f"Timeline with {len(sequence)} events across {len(mapped_tracks)} roles")
    print("\nEvents per role:")
    for role, events in mapped_tracks.items():
        print(f"  {role:15s}: {len(events):5d} events")

    return sequence, mapped_tracks

sequence, tracks = create_role_based_timeline('song.mid')

# Print first 10 events from timeline
print("\nFirst 10 events in timeline:")
for i, ev in enumerate(sequence[:10], 1):
    print(f"{i:2d}. {ev['start']:6.2f}s | Role: {ev['role']:10s} | Note: {ev['note']:3d}")
```

### Example 12: Export Analysis Results

```python
import json
from midi_processing import parse_midi, detect_key, analyze_chords, rhythm_pattern

def export_analysis_to_json(filepath, output_json):
    """Analyze MIDI and export results to JSON."""

    events = parse_midi(filepath)
    key = detect_key(events)
    chords = analyze_chords(events, window=0.5)
    patterns = rhythm_pattern(events, top_k=10)

    # Prepare data for export
    analysis = {
        'file': filepath,
        'total_events': len(events),
        'duration_seconds': events[-1]['end'] if events else 0,
        'key': key,
        'chords': [
            {
                'time': chord['time'],
                'root': chord['root'],
                'type': chord['type'],
                'notes': chord['notes']
            }
            for chord in chords
        ],
        'rhythm_patterns': [
            {'interval': interval, 'count': count}
            for interval, count in patterns
        ],
        'note_range': {
            'lowest': min(ev['note'] for ev in events) if events else None,
            'highest': max(ev['note'] for ev in events) if events else None
        }
    }

    # Export to JSON
    with open(output_json, 'w') as f:
        json.dump(analysis, f, indent=2)

    print(f"Analysis exported to {output_json}")
    return analysis

# Export analysis
results = export_analysis_to_json('song.mid', 'analysis_results.json')
```

---

## Real-World Scenarios

### Example 13: Batch Process Multiple MIDI Files

```python
import os
from midi_processing import parse_midi, detect_key

def batch_analyze_directory(directory):
    """Analyze all MIDI files in a directory."""

    results = []

    # Find all MIDI files
    midi_files = [f for f in os.listdir(directory) if f.endswith('.mid')]

    print(f"Found {len(midi_files)} MIDI files")
    print("-" * 70)

    for filename in midi_files:
        filepath = os.path.join(directory, filename)

        try:
            events = parse_midi(filepath)
            key = detect_key(events)
            duration = events[-1]['end'] if events else 0

            result = {
                'filename': filename,
                'events': len(events),
                'duration': duration,
                'key': key
            }
            results.append(result)

            print(f"{filename:30s} | {len(events):5d} events | {duration:6.1f}s | {key}")

        except Exception as e:
            print(f"{filename:30s} | ERROR: {e}")

    return results

# Analyze all MIDI files in a directory
results = batch_analyze_directory('midi_files/')

# Summary statistics
print("\n" + "=" * 70)
print("SUMMARY:")
print(f"Total files: {len(results)}")
print(f"Total events: {sum(r['events'] for r in results)}")
print(f"Total duration: {sum(r['duration'] for r in results)/60:.1f} minutes")

# Key distribution
from collections import Counter
keys = Counter(r['key'] for r in results)
print("\nKey distribution:")
for key, count in keys.most_common():
    print(f"  {key:15s}: {count:3d} files")
```

### Example 14: Transpose Detection (Detect Transposed Versions)

```python
from midi_processing import parse_midi, detect_key

def compare_midi_keys(file1, file2):
    """Compare keys of two MIDI files (useful for detecting transpositions)."""

    events1 = parse_midi(file1)
    events2 = parse_midi(file2)

    key1 = detect_key(events1)
    key2 = detect_key(events2)

    print(f"File 1: {file1}")
    print(f"  Key: {key1}")
    print(f"  Events: {len(events1)}")

    print(f"\nFile 2: {file2}")
    print(f"  Key: {key2}")
    print(f"  Events: {len(events2)}")

    if key1 == key2:
        print("\n✓ Files are in the same key")
    else:
        print(f"\n✗ Files are in different keys: {key1} vs {key2}")
        print("  (May be transposed versions)")

compare_midi_keys('original.mid', 'transposed.mid')
```

### Example 15: Find Similar Chord Progressions

```python
from midi_processing import parse_midi, analyze_chords

def extract_chord_progression(filepath, window=0.5):
    """Extract simplified chord progression."""
    events = parse_midi(filepath)
    chords = analyze_chords(events, window=window)

    # Simplify to just root and type
    progression = [
        f"{chord['root']} {chord['type']}"
        for chord in chords
        if chord['root'] is not None
    ]

    return progression

def compare_progressions(file1, file2):
    """Compare chord progressions between two files."""

    prog1 = extract_chord_progression(file1)
    prog2 = extract_chord_progression(file2)

    print(f"File 1: {file1}")
    print(f"  Progression: {' | '.join(prog1[:8])}")
    print(f"  Total chords: {len(prog1)}")

    print(f"\nFile 2: {file2}")
    print(f"  Progression: {' | '.join(prog2[:8])}")
    print(f"  Total chords: {len(prog2)}")

    # Calculate similarity (simple Jaccard index)
    set1 = set(prog1)
    set2 = set(prog2)
    similarity = len(set1 & set2) / len(set1 | set2) if set1 or set2 else 0

    print(f"\nSimilarity: {similarity:.2%}")
    print(f"Common chords: {set1 & set2}")

compare_progressions('song1.mid', 'song2.mid')
```

### Example 16: Generate Practice MIDI Sections

```python
from midi_processing import parse_midi, align_notes

def extract_practice_sections(filepath, section_duration=8.0):
    """Split MIDI into practice sections of specified duration."""

    events = parse_midi(filepath)
    aligned = align_notes(events, quantize=0.125)

    total_duration = aligned[-1]['end'] if aligned else 0
    num_sections = int(total_duration / section_duration) + 1

    sections = []
    for i in range(num_sections):
        start_time = i * section_duration
        end_time = (i + 1) * section_duration

        section_events = [
            ev for ev in aligned
            if ev['start'] >= start_time and ev['start'] < end_time
        ]

        if section_events:
            sections.append({
                'section': i + 1,
                'start': start_time,
                'end': end_time,
                'events': section_events
            })

    print(f"Split {filepath} into {len(sections)} sections:")
    for section in sections:
        print(f"  Section {section['section']}: "
              f"{section['start']:.1f}s - {section['end']:.1f}s "
              f"({len(section['events'])} notes)")

    return sections

# Extract 8-second practice sections
sections = extract_practice_sections('difficult_piece.mid', section_duration=8.0)

# You could then save each section as a separate MIDI file
# (requires additional mido code for writing MIDI files)
```

### Example 17: Analyze Playing Difficulty

```python
from midi_processing import parse_midi, rhythm_pattern

def estimate_difficulty(filepath):
    """Estimate playing difficulty based on various metrics."""

    events = parse_midi(filepath)

    # Calculate metrics
    duration = events[-1]['end'] if events else 0
    note_density = len(events) / duration if duration > 0 else 0

    # Note range
    notes = [ev['note'] for ev in events]
    note_range = max(notes) - min(notes) if notes else 0

    # Rhythm complexity (variety of intervals)
    patterns = rhythm_pattern(events, top_k=20)
    rhythm_complexity = len(patterns)

    # Average velocity (dynamics)
    avg_velocity = sum(ev['velocity'] for ev in events) / len(events) if events else 0

    # Polyphony (max simultaneous notes)
    max_polyphony = 0
    time_steps = [ev['start'] for ev in events]
    for t in set(time_steps):
        active = sum(1 for ev in events if ev['start'] <= t < ev['end'])
        max_polyphony = max(max_polyphony, active)

    # Scoring
    difficulty_score = 0
    difficulty_score += min(note_density / 5, 10)  # Max 10 points
    difficulty_score += min(note_range / 4, 10)    # Max 10 points
    difficulty_score += min(rhythm_complexity, 10)  # Max 10 points
    difficulty_score += min(max_polyphony * 2, 10)  # Max 10 points

    # Normalize to 0-100
    difficulty_score = (difficulty_score / 40) * 100

    print(f"Difficulty Analysis for {filepath}")
    print("=" * 60)
    print(f"Note density:       {note_density:.2f} notes/second")
    print(f"Note range:         {note_range} semitones")
    print(f"Rhythm complexity:  {rhythm_complexity} distinct patterns")
    print(f"Max polyphony:      {max_polyphony} simultaneous notes")
    print(f"Average velocity:   {avg_velocity:.1f}")
    print(f"\nOverall difficulty: {difficulty_score:.1f}/100")

    if difficulty_score < 30:
        print("Level: Beginner")
    elif difficulty_score < 50:
        print("Level: Intermediate")
    elif difficulty_score < 70:
        print("Level: Advanced")
    else:
        print("Level: Expert")

    return difficulty_score

difficulty = estimate_difficulty('complex_piece.mid')
```

---

## Tips for Using These Examples

1. **Start Simple**: Begin with basic examples and gradually move to advanced ones.

2. **Modify Parameters**: Experiment with different parameter values to see their effects.

3. **Error Handling**: Add try-except blocks for production code:
   ```python
   try:
       events = parse_midi('song.mid')
   except Exception as e:
       print(f"Error parsing MIDI: {e}")
   ```

4. **Visualize Results**: Consider using matplotlib or other libraries to visualize analysis results.

5. **Combine Examples**: Mix and match code from different examples to create custom workflows.

For more information, see the [API Reference](API.md) and [Configuration Documentation](CONFIGURATION.md).
