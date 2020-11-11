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


from abc import ABC, abstractmethod
    
class Recording(ABC):
    """ Abstract class representing data from a single Recording
    
    Classes for different data formats should inherit from this class.
    
    Recording objects contain three properties:
        - continuous
        - events
        - spikes
    
    which load the underlying data upon access.
    
    continuous is a list of data streams
        - samples (memory-mapped array of dimensions samples x channels)
        - timestamps (array of length samples)
        - metadata (contains information about the data source)
        
    spikes is a list of spike sources
        - waveforms (spikes x channels x samples)
        - timestamps (one per spikes)
        - electrodes (index of electrode from which each spike originated)
        - metadata (contains information about each electrode)
        
    Event data is stored in a pandas DataFrame containing four columns:
        - timestamp
        - channel
        - nodeId (processor ID)
        - state (1 or 0)
    
    """
    
    @property
    def continuous(self):
        if self._continuous is None:
            self.load_continuous()
        return self._continuous

    @property
    def events(self):
        if self._events is None:
            self.load_events()
        return self._events

    @property
    def spikes(self):
        if self._spikes is None:
            self.load_spikes()
        return self._spikes
    
    def __init__(self, directory, experiment_index, recording_index):
        """ Construct a Recording object, which provides access to
        data from one recording (start/stop acquisition or start/stop recording)

        Parameters
        ----------
        directory : string
            path to Record Node directory (e.g. 'Record Node 108')
        experiment_index : int
            0-based index of experiment
        recording_index : int
            0-based index of recording
        
        """
        
        self.directory = directory
        self.experiment_index = experiment_index
        self.recording_index = recording_index
        
        self._continuous = None
        self._events = None
        self._spikes = None
        
    @abstractmethod
    def load_spikes(self):
        pass
    
    @abstractmethod
    def load_events(self):
        pass
    
    @abstractmethod
    def load_continuous(self):
        pass
    
    @abstractmethod
    def detect_format(directory):
        """Return True if the format matches the Record Node directory contents"""
        pass
    
    @abstractmethod
    def detect_recordings(directory):
        """Finds Recordings within a Record Node directory"""
        pass
    
    @abstractmethod
    def __str__(self):
        """Returns a string with information about the Recording"""
        pass
    
    
        
    