"""
MIT License

Copyright (c) 2020-2025 Open Ephys
Copyright (c) 2025 Joscha Schmiedt (joscha@schmiedt.dev)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
from enum import Enum
from open_ephys.analysis.formats import (
    OpenEphysRecording,
    BinaryRecording,
    NwbRecording,
)
from open_ephys.analysis.recording import RecordingFormat, Recording


class RecordNode:
    recordings: list[Recording]
    directory: str

    """A 'RecordNode' object represents a directory containing data from
    one Open Ephys Record Node.

    Each Record Node placed in the signal chain will write data to its own
    directory.

    A RecordNode object contains a list of Recordings that can be accessed via:

        recordnode.recordings[n]

    where N is the index of the Recording (e.g., 0, 1, 2, ...)

    """

    def __init__(self, directory: str, mmap_timestamps: bool = True):
        """Construct a RecordNode object, which provides access to
        data from one Open Ephys Record Node

        Parameters
        ----------
        directory: location of Record Node directory

        mmap_timestamps: bool, optional
            If True, timestamps will be memory-mapped for faster access
            (default is True). Set to False if you plan to overwrite the
            timestamps files in the session directory.
        """

        self.directory = directory

        self._detect_format()

        self._detect_recordings(mmap_timestamps)

    def _detect_format(self):
        """
        Internal method used to detect a Record Node's data format upon
        initialization.
        """

        self.format_class_map = {
            RecordingFormat.nwb: NwbRecording,
            RecordingFormat.binary: BinaryRecording,
            RecordingFormat.openephys: OpenEphysRecording,
        }

        for format_key in self.format_class_map.keys():
            if self.format_class_map[format_key].detect_format(self.directory):
                self.format = format_key
                return

        raise (IOError("No available data format detected."))

    def _detect_recordings(self, mmap_timestamps):
        """
        Internal method used to detect Recordings upon initialization
        """

        self.recordings = self.format_class_map[self.format].detect_recordings(
            self.directory, mmap_timestamps
        )

    def __str__(self):
        """Returns a string with information about the RecordNode"""

        return os.path.basename(self.directory) + " (" + self.format + " format)"
