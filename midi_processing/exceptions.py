"""midi_processing.exceptions

Custom exception classes for MIDI processing errors.
"""


class MIDIProcessingError(Exception):
    """Base exception for all MIDI processing errors."""
    pass


class MIDIParsingError(MIDIProcessingError):
    """Exception raised when MIDI file parsing fails."""
    pass


class ConfigurationError(MIDIProcessingError):
    """Exception raised when configuration is invalid."""
    pass


class InvalidInputError(MIDIProcessingError):
    """Exception raised when input parameters are invalid."""

    def __init__(self, message: str, parameter_name: str = None, expected: str = None):
        super().__init__(message)
        self.parameter_name = parameter_name
        self.expected = expected
