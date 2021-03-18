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

import glob
import os

import warnings

from open_ephys.analysis.recordnode import RecordNode

class Session:
    
    """Each 'Session' object represents a top-level directory containing data from
    one or more Record Nodes.
    
    A new directory is automatically started when launching Open Ephys, or after
    pressing the '+' button in the record options section of the control panel.
    
    A Session object contains a list of Record Nodes that can be accessed via:
        
        session.recordnodes[n]
        
    where N is the index of the Record Node (e.g., 0, 1, 2, ...)
    
    """
    
    def __init__(self, directory):
        """ Construct a session object, which provides access to
        data from multiple Open Ephys Record Nodes

        Parameters
        ----------
        directory: path to the session directory
        """
        
        self.directory = directory;
        
        self._detect_record_nodes()
        
        
    def _detect_record_nodes(self):
        """
        Internal method used to detect Record Nodes upon initialization.
        """
        
        recordnodepaths = glob.glob(os.path.join(self.directory, 
                                             'Record Node *'))
        recordnodepaths.sort()
        
        if len(recordnodepaths) == 0:

            self.recordings = RecordNode(self.directory).recordings

        else:

            self.recordnodes = [RecordNode(path) for path in recordnodepaths]

    def __str__(self):
        """Returns a string with information about the Session"""
        
        return ''.join(["\nOpen Ephys Recording Session Object\n",
                        "Directory: " + self.directory + "\n\n"
                        "<object>.recordnodes:\n"] + 
                        ["  Index " + str(i) + ": " + r.__str__() + "\n" 
                          for i, r in enumerate(self.recordnodes)])

