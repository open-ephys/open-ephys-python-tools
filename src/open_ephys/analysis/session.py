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

import glob
import os

from open_ephys.analysis.recordnode import RecordNode
from open_ephys.analysis.utils import alphanum_key


class Session:
    """Each 'Session' object represents a top-level directory containing data
    from one or more Record Nodes.

    A new directory is automatically started when launching Open Ephys, or
    after pressing the '+' button in the record options section of the control
    panel.

    A Session object contains a list of Record Nodes that can be accessed via:

        session.recordnodes[n]

    where N is the index of the Record Node (e.g., 0, 1, 2, ...)

    """

    directory: str
    mmap_timestamps: bool
    recordnodes: list[RecordNode] | None

    def __init__(self, directory, mmap_timestamps=True):
        """Construct a session object, which provides access to
        data from multiple Open Ephys Record Nodes

        Parameters
        ----------
        directory: path to the session directory
        memmap_timestamps: bool, optional
            If True, timestamps will be memory-mapped for faster access
            (default is True). Set to False if you plan to overwrite the
            timestamps files in the session directory.
        """

        self.directory = directory
        self.mmap_timestamps = mmap_timestamps

        self._detect_record_nodes()

    def _detect_record_nodes(self):
        """
        Internal method used to detect Record Nodes upon initialization.
        """

        recordnodepaths = glob.glob(os.path.join(self.directory, "Record Node *"))
        recordnodepaths.sort(key=alphanum_key)

        if len(recordnodepaths) == 0:
            self.recordings = RecordNode(
                self.directory, self.mmap_timestamps
            ).recordings

        else:
            self.recordnodes = [
                RecordNode(path, self.mmap_timestamps) for path in recordnodepaths
            ]

    def __str__(self):
        """Returns a string with information about the Session"""

        return "".join(
            [
                "\nOpen Ephys Recording Session Object\n",
                "Directory: " + self.directory + "\n\n<object>.recordnodes:\n",
            ]
            + [
                "  Index " + str(i) + ": " + r.__str__() + "\n"
                for i, r in enumerate(self.recordnodes)
            ]
        )
