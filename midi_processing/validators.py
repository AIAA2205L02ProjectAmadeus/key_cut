"""midi_processing.validators

Input validation functions for MIDI processing.
"""
import os
from typing import List, Dict, Any


class ValidationError(Exception):
    """Exception raised when validation fails."""
    pass


def validate_midi_file_path(path: str) -> None:
    """Validate MIDI file path exists and is readable.

    Args:
        path: Path to MIDI file

    Raises:
        ValidationError: If path is invalid or file doesn't exist
    """
    if not isinstance(path, str):
        raise ValidationError(f"path must be a string, got {type(path).__name__}")
    if not path:
        raise ValidationError("path cannot be empty")
    if not os.path.exists(path):
        raise ValidationError(f"MIDI file not found: {path}")
    if not os.path.isfile(path):
        raise ValidationError(f"path is not a file: {path}")


def validate_ticks_per_beat(ticks_per_beat: int) -> None:
    """Validate ticks per beat value.

    Args:
        ticks_per_beat: Ticks per beat value

    Raises:
        ValidationError: If value is invalid
    """
    if not isinstance(ticks_per_beat, int):
        raise ValidationError(f"ticks_per_beat must be an integer, got {type(ticks_per_beat).__name__}")
    if ticks_per_beat <= 0:
        raise ValidationError(f"ticks_per_beat must be positive, got {ticks_per_beat}")


def validate_tempo(tempo: int) -> None:
    """Validate tempo value (microseconds per beat).

    Args:
        tempo: Tempo in microseconds per beat

    Raises:
        ValidationError: If tempo is invalid
    """
    if not isinstance(tempo, int):
        raise ValidationError(f"tempo must be an integer, got {type(tempo).__name__}")
    if tempo <= 0:
        raise ValidationError(f"tempo must be positive, got {tempo}")


def validate_note_events_list(events: List[Dict[str, Any]], strict: bool = True) -> None:
    """Validate list of note events.

    Args:
        events: List of note event dictionaries
        strict: If True, validate each event has required fields

    Raises:
        ValidationError: If events list is invalid
    """
    if not isinstance(events, list):
        raise ValidationError(f"events must be a list, got {type(events).__name__}")

    if strict and events:
        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                raise ValidationError(f"Event at index {i} must be a dictionary, got {type(ev).__name__}")
            if 'note' not in ev:
                raise ValidationError(f"Event at index {i} missing required field 'note'")
            if 'start' not in ev:
                raise ValidationError(f"Event at index {i} missing required field 'start'")


def validate_window_size(window: float) -> None:
    """Validate window size for chord analysis.

    Args:
        window: Window size in seconds

    Raises:
        ValidationError: If window size is invalid
    """
    if not isinstance(window, (int, float)):
        raise ValidationError(f"window must be a number, got {type(window).__name__}")
    if window <= 0:
        raise ValidationError(f"window must be positive, got {window}")


def validate_top_k(top_k: int) -> None:
    """Validate top_k parameter.

    Args:
        top_k: Number of top items to return

    Raises:
        ValidationError: If top_k is invalid
    """
    if not isinstance(top_k, int):
        raise ValidationError(f"top_k must be an integer, got {type(top_k).__name__}")
    if top_k < 1:
        raise ValidationError(f"top_k must be at least 1, got {top_k}")


def validate_quantize_value(quantize: float) -> None:
    """Validate quantization value.

    Args:
        quantize: Quantization grid size in seconds

    Raises:
        ValidationError: If quantize value is invalid
    """
    if not isinstance(quantize, (int, float)):
        raise ValidationError(f"quantize must be a number, got {type(quantize).__name__}")
    if quantize <= 0:
        raise ValidationError(f"quantize must be positive, got {quantize}")


def validate_track_mapping(mapping: Dict[str, str]) -> None:
    """Validate track mapping dictionary.

    Args:
        mapping: Dictionary mapping patterns to roles

    Raises:
        ValidationError: If mapping is invalid
    """
    if not isinstance(mapping, dict):
        raise ValidationError(f"mapping must be a dictionary, got {type(mapping).__name__}")

    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValidationError(f"mapping keys must be strings, got {type(key).__name__}")
        if not isinstance(value, str):
            raise ValidationError(f"mapping values must be strings, got {type(value).__name__}")


def validate_config_path(config_path: str) -> None:
    """Validate configuration file path.

    Args:
        config_path: Path to configuration file

    Raises:
        ValidationError: If path is invalid
    """
    if not isinstance(config_path, str):
        raise ValidationError(f"config_path must be a string, got {type(config_path).__name__}")
    if not config_path:
        raise ValidationError("config_path cannot be empty")
