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
import warnings
    
class Recording(ABC):
    """ Abstract class representing data from a single Recording
    
    Classes for different data formats should inherit from this class.
    
    Recording objects contain three properties:
        - continuous
        - events
        - spikes
        - messages
    
    which load the underlying data upon access.
    
    continuous is a list of data streams
        - samples (memory-mapped array of dimensions samples x channels)
        - sample_numbers (array of length samples)
        - timestamps (array of length samples)
        - metadata (contains information about the data source)
            - channel_names
            - bit_volts
            - source_node_id
            - stream_name
        
    spikes is a list of spike sources
        - waveforms (spikes x channels x samples)
        - sample_numbers (one per sample)
        - timestamps (one per sample)
        - electrodes (index of electrode from which each spike originated)
        - metadata (contains information about each electrode)
            - electrode_names
            - bit_volts
            - source_node_id
            - stream_name
        
    events is a pandas DataFrame containing six columns:
        - timestamp
        - sample_number
        - line
        - state (1 or 0)
        - processor_id
        - stream_index

    messages is a pandas DataFrame containing three columns:
        - timestamp
        - sample_number
        - message
    
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

    @property
    def messages(self):
        if self._messages is None:
            self.load_messages()
        return self._messages
    
    @property
    def format(self):
        return self._format
    
    def __init__(self, directory, experiment_index=0, recording_index=0):
        """ Construct a Recording object, which provides access to
        data from one recording (start/stop acquisition or start/stop recording)

        Parameters
        ----------
        directory : string
            path to Record Node directory (e.g. 'Record Node 108')
        experiment_index : int
            0-based index of experiment
            defaults to 0
        recording_index : int
            0-based index of recording
            defaults to 0
        
        """
        
        self.directory = directory
        self.experiment_index = experiment_index
        self.recording_index = recording_index
        
        self._continuous = None
        self._events = None
        self._spikes = None
        self._messages = None
        
        self.sync_lines = []
        
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
    def load_messages(self):
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
    
    def add_sync_line(self, line, processor_id, stream_name=None, main=False, ignore_intervals=[]):
        """Specifies an event channel to use for timestamp synchronization. Each 
        sync line in a recording should receive its input from the same 
        physical digital input line.
        
        For synchronization to work, there must be one (and only one) 'main' 
        sync line, to which all timestamps will be aligned.
        
        Parameters
        ----------
        line : int
            event line number (1-based indexing)
        processor_id : int
            ID for the processor receiving sync events (eg 101)
        stream_name : str
            name of the stream receiving sync events (eg 'Probe-A-AP')
            default = None
        main : bool
            if True, this stream's timestamps will be treated as the 
            main clock
        ignore_intervals : list of tuples
            intervals to ignore when checking for common events
            default = []
        
        """

        events_on_line = self.events[(self.events.line == line) &
                                     (self.events.processor_id == processor_id) &
                                     (self.events.stream_name == stream_name)]
        

        if len(events_on_line) == 0:
            raise Exception('No events found on this line. ' + 
                            'Check that the processor ID and stream name are correct.')
        
        if main:
            existing_main = [sync for sync in self.sync_lines 
                             if sync['main']]
            
            if len(existing_main) > 0:
                raise Exception('Another main sync line already exists. ' + 
                                'To override, add it again with main=False.')
                
        matching_node = [sync for sync in self.sync_lines 
                         if sync['processor_id'] == processor_id and
                            sync['stream_name'] == stream_name]
        
        if len(matching_node) == 1:
            self.sync_lines.remove(matching_node[0])
            warnings.warn('Another sync line exists for this processor/stream combination, overwriting.')

        self.sync_lines.append({'line' : line,
                                'processor_id' : processor_id,
                                'stream_name' : stream_name,
                                'main' : main,
                                'ignore_intervals' : ignore_intervals})
        
    def compute_global_timestamps(self, overwrite=False):
        """After sync channels have been added, this function computes the
        global timestamps for all processors with a shared sync line.

        Parameters
        ----------
        overwrite : bool
            if True, overwrite existing timestamps
            if False, add an extra "global_timestamp" column
            default = False
        
        """
        
        if len(self.sync_lines) == 0:
            raise Exception('At least two sync lines must be specified ' + 
                            'using `add_sync_line` before global timestamps ' + 
                            'can be computed.')

        main_line = [sync for sync in self.sync_lines 
                             if sync['main']]
        
        aux_lines = [sync for sync in self.sync_lines 
                             if not sync['main']]
            
        if len(main_line) == 0:
            raise Exception('Computing global timestamps requires one ' + 
                            'main sync line to be specified.')
            
        main_line = main_line[0]

        main_events = self.events[(self.events.line == main_line['line']) & 
                   (self.events.processor_id == main_line['processor_id']) & 
                   (self.events.stream_name == main_line['stream_name']) &
                   (self.events.state == 1)]
        
        # sort by sample number, in case the original timestamps were incorrect
        main_events = main_events.sort_values(by='sample_number')

        # remove any events that fall within the ignore intervals
        for ignore_interval in main_line['ignore_intervals']:
            main_events = main_events[(main_events.sample_number < ignore_interval[0]) |
                                      (main_events.sample_number > ignore_interval[1])]
        
        main_start_sample = main_events.iloc[0].sample_number
        main_total_samples = main_events.iloc[-1].sample_number - main_start_sample
        main_line['start'] = main_start_sample
        main_line['scaling'] = 1
        main_line['offset'] = main_start_sample

        for continuous in self.continuous:

            if (continuous.metadata['source_node_id'] == main_line['processor_id']) and \
               (continuous.metadata['stream_name'] == main_line['stream_name']):
               main_line['sample_rate'] = continuous.metadata['sample_rate']
        
        print(f'Processor ID: {main_line["processor_id"]}, Stream Name: {main_line["stream_name"]}, Line: {main_line["line"]} (main sync line))')
        print(f'  First event sample number: {main_line["start"]}')
        print(f'  Last event sample number: {main_total_samples - main_line["start"]}')
        print(f'  Total sync events: {len(main_events)}')
        print(f'  Sample rate: {main_line["sample_rate"]}')

        for aux in aux_lines:
            
            aux_events = self.events[(self.events.line == aux['line']) &
                   (self.events.processor_id == aux['processor_id']) &
                   (self.events.stream_name == aux['stream_name']) &
                   (self.events.state == 1)]
            
            # sort by sample number, in case the original timestamps were incorrect
            aux_events = aux_events.sort_values(by='sample_number')

            # remove any events that fall within the ignore intervals
            for ignore_interval in aux['ignore_intervals']:
                aux_events = aux_events[(aux_events.sample_number < ignore_interval[0]) |
                                      (aux_events.sample_number > ignore_interval[1])]
            
            aux_start_sample = aux_events.iloc[0].sample_number
            aux_total_samples = aux_events.iloc[-1].sample_number - aux_start_sample
            
            aux['start'] = aux_start_sample
            aux['scaling'] = main_total_samples / aux_total_samples
            aux['offset'] = main_start_sample
            aux['sample_rate'] = main_line['sample_rate']

            print(f'Processor ID: {aux["processor_id"]}, Stream Name: {aux["stream_name"]}, Line: {main_line["line"]} (aux sync line))')
            print(f'  First event sample number: {aux["start"]}')
            print(f'  Last event sample number: {aux_total_samples - aux["start"]}')
            print(f'  Total sync events: {len(aux_events)}')
            print(f'  Scale factor: {aux["scaling"]}')
            print(f'  Actual sample rate: {aux["sample_rate"] / aux["scaling"]}')

        for sync_line in self.sync_lines: # loop through all sync lines
            
            for continuous in self.continuous:

                if (continuous.metadata['source_node_id'] == sync_line['processor_id']) and \
                   (continuous.metadata['stream_name'] == sync_line['stream_name']):
                       
                    continuous.global_timestamps = \
                        ((continuous.sample_numbers - sync_line['start']) * sync_line['scaling'] \
                            + sync_line['offset']) 
                    
                    global_timestamps = continuous.global_timestamps / sync_line['sample_rate'] / sync_line['scaling']
                            
                    if overwrite:
                        continuous.timestamps = global_timestamps
                    else:
                        continuous.global_timestamps = global_timestamps
                            
            event_inds = self.events[(self.events.processor_id == sync_line['processor_id']) & 
                   (self.events.stream_name == sync_line['stream_name'])].index.values

            global_timestamps = (self.events.loc[event_inds].sample_number - sync_line['start']) \
                                  * sync_line['scaling'] \
                                   + sync_line['offset']
                                   
            global_timestamps = global_timestamps / sync_line['sample_rate']
            
            if overwrite:
                self.events.loc[event_inds, 'timestamp'] = global_timestamps
            else:
                for ind, ts in zip(event_inds, global_timestamps):
                    self.events.at[ind, 'global_timestamp'] = ts
    
                                              
        
        
    
        
    
