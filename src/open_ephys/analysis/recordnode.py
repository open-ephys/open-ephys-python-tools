"""
MIT License

Copyright (c) 2020 Open Ephys

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
import glob

from open_ephys.analysis.formats import OpenEphysRecording, BinaryRecording, NwbRecording

class RecordNode:
    
    """A 'RecordNode' object represents a directory containing data from
    one Open Ephys Record Node.
    
    Each Record Node placed in the signal chain will write data to its own
    directory.
    
    A RecordNode object contains a list of Recordings that can be accessed via:
        
        recordnode.recordings[n]
        
    where N is the index of the Recording (e.g., 0, 1, 2, ...)
    
    """
    
    def __init__(self, directory):
        """ Construct a RecordNode object, which provides access to
        data from one Open Ephys Record Node

        Parameters
        ----------
        directory: location of Record Node directory
        """
        
        self.directory = directory
        
        self._detect_format()
        
        self._detect_recordings()
        
        
    def _detect_format(self):
        """
        Internal method used to detect a Record Node's data format upon initialization.
        """
        
        self.formats = {'nwb': NwbRecording,
                        'binary': BinaryRecording,
                        'open-ephys': OpenEphysRecording}
        
        for format_key in self.formats.keys():
            if self.formats[format_key].detect_format(self.directory):
                self.format = format_key
                return
        
        raise(IOError('No available data format detected.'))
        
        
    def _detect_recordings(self):
        """
        Internal method used to detect Recordings upon initialization
        """
        
        self.recordings = self.formats[self.format].detect_recordings(self.directory)

    def __str__(self):
        """Returns a string with information about the RecordNode"""
        
        return os.path.basename(self.directory) + " (" + self.format + " format)"
               
               