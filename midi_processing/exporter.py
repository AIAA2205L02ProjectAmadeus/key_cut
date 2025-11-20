"""midi_processing.exporter

Export analysis results to various formats (JSON, CSV, YAML, text).
"""
import json
import csv
from typing import Dict, Any, List
from pathlib import Path
from .analysis_result import AnalysisResult


class ExportError(Exception):
    """Exception raised when export fails."""
    pass


def export_json(result: AnalysisResult, output_path: str) -> None:
    """Export analysis result to JSON file.

    Args:
        result: AnalysisResult instance
        output_path: Path to output JSON file

    Raises:
        ExportError: If export fails
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ExportError(f"Failed to export JSON: {e}")


def export_csv(result: AnalysisResult, output_path: str) -> None:
    """Export analysis result to CSV file (events only).

    Args:
        result: AnalysisResult instance
        output_path: Path to output CSV file

    Raises:
        ExportError: If export fails
    """
    try:
        if not result.events:
            raise ExportError("No events to export")

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = list(result.events[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result.events)
    except Exception as e:
        raise ExportError(f"Failed to export CSV: {e}")


def export_yaml(result: AnalysisResult, output_path: str) -> None:
    """Export analysis result to YAML file.

    Args:
        result: AnalysisResult instance
        output_path: Path to output YAML file

    Raises:
        ExportError: If export fails
    """
    try:
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(result.to_dict(), f, default_flow_style=False, allow_unicode=True)
    except ImportError:
        raise ExportError("PyYAML is required for YAML export. Install with: pip install pyyaml")
    except Exception as e:
        raise ExportError(f"Failed to export YAML: {e}")


def export_text(result: AnalysisResult, output_path: str) -> None:
    """Export analysis result to human-readable text file.

    Args:
        result: AnalysisResult instance
        output_path: Path to output text file

    Raises:
        ExportError: If export fails
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== Music Analysis Report ===\n\n")

            if result.key:
                f.write(f"Detected Key: {result.key}\n\n")

            if result.track_mapping:
                f.write("Track Mapping:\n")
                for track, role in result.track_mapping.items():
                    f.write(f"  {track}: {role}\n")
                f.write("\n")

            if result.chords:
                f.write(f"Chords ({len(result.chords)} total):\n")
                for chord in result.chords[:20]:
                    time = chord.get('time', 0)
                    root = chord.get('root', 'Unknown')
                    chord_type = chord.get('type', 'Unknown')
                    f.write(f"  {time:.2f}s: {root} {chord_type}\n")
                if len(result.chords) > 20:
                    f.write(f"  ... and {len(result.chords) - 20} more\n")
                f.write("\n")

            if result.rhythm_patterns:
                f.write("Top Rhythm Patterns:\n")
                for interval, count in result.rhythm_patterns:
                    f.write(f"  Interval: {interval:.4f}s, Count: {count}\n")
                f.write("\n")

            if result.events:
                f.write(f"Total Events: {len(result.events)}\n")
                if result.events:
                    start = min(e.get('start', 0) for e in result.events)
                    end = max(e.get('end', 0) for e in result.events)
                    f.write(f"Duration: {end - start:.2f}s\n")

    except Exception as e:
        raise ExportError(f"Failed to export text: {e}")


def export_analysis(result: AnalysisResult, output_path: str, format: str = 'json') -> None:
    """Export analysis result to specified format.

    Args:
        result: AnalysisResult instance
        output_path: Path to output file
        format: Export format ('json', 'csv', 'yaml', 'text')

    Raises:
        ExportError: If format is unsupported or export fails
    """
    format = format.lower()

    if format == 'json':
        export_json(result, output_path)
    elif format == 'csv':
        export_csv(result, output_path)
    elif format == 'yaml':
        export_yaml(result, output_path)
    elif format == 'text' or format == 'txt':
        export_text(result, output_path)
    else:
        raise ExportError(f"Unsupported export format: {format}. Supported formats: json, csv, yaml, text")
