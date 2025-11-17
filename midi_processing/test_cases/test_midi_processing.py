import tempfile
import os
from mido import Message, MidiFile, MidiTrack, bpm2tempo
from midi_processing import midi_parser, track_mapper, music_analyzer


def create_test_midi(path):
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    # tempo
    track.append(Message('program_change', program=0, time=0))
    from mido import MetaMessage
    track.append(MetaMessage('set_tempo', tempo=bpm2tempo(120), time=0))
    # C major arpeggio
    track2 = MidiTrack()
    mid.tracks.append(track2)
    # notes: C4, E4, G4
    track2.append(Message('note_on', note=60, velocity=64, time=0))
    track2.append(Message('note_off', note=60, velocity=64, time=480))
    track2.append(Message('note_on', note=64, velocity=64, time=0))
    track2.append(Message('note_off', note=64, velocity=64, time=480))
    track2.append(Message('note_on', note=67, velocity=64, time=0))
    track2.append(Message('note_off', note=67, velocity=64, time=480))

    mid.save(path)


def test_end_to_end():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mid')
    tmp.close()
    try:
        create_test_midi(tmp.name)
        events = midi_parser.parse_midi(tmp.name)
        assert len(events) >= 3
        # mapping by program
        mapping = track_mapper.map_tracks_from_parser_events(events)
        assert isinstance(mapping, dict)
        # key detection
        key = music_analyzer.detect_key(events)
        assert 'major' in key or 'minor' in key
        chords = music_analyzer.analyze_chords(events, window=1.0)
        assert len(chords) >= 1
        # rhythm
        rp = music_analyzer.rhythm_pattern(events)
        assert isinstance(rp, list)
    finally:
        os.unlink(tmp.name)
