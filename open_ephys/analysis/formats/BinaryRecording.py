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
import numpy as np
import pandas as pd
import json

from open_ephys.analysis.recording import Recording

class BinaryRecording(Recording):
    
    class Spikes:
        
        def __init__(self, info, base_directory):
        
            directory = os.path.join(base_directory, 'spikes', info['folder'])
            
            self.sample_numbers = np.load(os.path.join(directory, 'sample_numbers.npy'))
            self.timestamps = np.load(os.path.join(directory, 'timestamps.npy'))
            self.electrodes = np.load(os.path.join(directory, 'electrode_indices.npy')) - 1
        
            self.waveforms = np.load(os.path.join(directory, 'waveforms.npy'))
            
            if self.waveforms.ndim == 2:
                self.waveforms = np.expand_dims(self.waveforms, 1)

            self.clusters = np.load(os.path.join(directory, 'clusters.npy'))

            self.summary = pd.DataFrame(data = {'sample_number' : self.sample_numbers,
                    'timestamp' : self.timestamps,
                    'electrode' : self.electrodes,
                    'cluster' : self.clusters})
    
    class Continuous:
        
        def __init__(self, info, base_directory):
            
            directory = os.path.join(base_directory, 'continuous', info['folder_name'])

            self.name = info['folder_name']

            self.metadata = {}
            self.metadata['sample_rate'] = info['sample_rate']
            self.metadata['num_channels'] = info['num_channels']
            self.metadata['processor_id'] = info['source_processor_id']
            self.metadata['stream_name'] = info['stream_name']
            self.metadata['names'] = [ch['channel_name'] for ch in info['channels']]
            
            self.sample_numbers = np.load(os.path.join(directory, 'sample_numbers.npy'))
            self.timestamps = np.load(os.path.join(directory, 'timestamps.npy'))

            data = np.memmap(os.path.join(directory, 'continuous.dat'), mode='r', dtype='int16')
            self.samples = data.reshape((len(data) // self.metadata['num_channels'], 
                                         self.metadata['num_channels']))

            self.global_timestamps = None
    
    def __init__(self, directory, experiment_index=0, recording_index=0):
        
       Recording.__init__(self, directory, experiment_index, recording_index)  
       
       self.info = json.load(open(os.path.join(self.directory, 'structure.oebin')))
       self._format = 'binary'
       
    def load_continuous(self):
        
        
        self._continuous = []
        
        
        for info in self.info['continuous']:
            
            try:
                c = self.Continuous(info, self.directory)
            except FileNotFoundError:
                pass
            else:
                self._continuous.append(c)
            
    def load_spikes(self):
        
        self._spikes = []
        
        self._spikes.extend([self.Spikes(info, self.directory) for info in self.info['spikes']])

    
    def load_events(self):
        search_string = os.path.join(self.directory,
                                    'events',
                                    '*',
                                    'TTL*')
        
        events_directories = glob.glob(search_string)
        
        df = []
        
        streamIdx = -1
        
        for events_directory in events_directories:
            
            node_name = os.path.basename(os.path.dirname(events_directory)).split('.')
            node = node_name[0]
            nodeId = node.split("-")[-1]
            stream = ''.join(node_name[1:])
            
            streamIdx += 1
            
            channels = np.load(os.path.join(events_directory, 'states.npy'))
            sample_numbers = np.load(os.path.join(events_directory, 'sample_numbers.npy'))
            timestamps = np.load(os.path.join(events_directory, 'timestamps.npy'))
        
            df.append(pd.DataFrame(data = {'line' : np.abs(channels),
                              'sample_number' : sample_numbers,
                              'timestamp' : timestamps,
                              'processor_id' : [nodeId] * len(channels),
                              'stream_index' : [streamIdx] * len(channels),
                              'state' : (channels > 0).astype('int')}))
            
        
            
        if len(df) > 0:
                                               
            self._events = pd.concat(df).sort_values(by=['timestamp', 'stream_index'], ignore_index=True)

        else:
            
            self._events = None
    
    def load_messages(self):
        search_string = os.path.join(self.directory,
                            'events',
                            'MessageCenter')
        msg_center_dir = glob.glob(search_string)

        df = []

        if len(msg_center_dir) == 1:

            msg_center_dir = msg_center_dir[0]
            sample_numbers = np.load(os.path.join(msg_center_dir, 'sample_numbers.npy'))
            timestamps = np.load(os.path.join(msg_center_dir, 'timestamps.npy'))
            text = np.load(os.path.join(msg_center_dir, 'text.npy'))

            df = pd.DataFrame(data = { 'sample_number' : sample_numbers,
                    'timestamp' : timestamps,
                    'message' : text} )

        if len(df) > 0:

            self._messages = df;

        else:

            self._messages = None

    def __str__(self):
        """Returns a string with information about the Recording"""
        
        return "Open Ephys GUI Recording\n" + \
                "ID: " + hex(id(self)) + '\n' + \
                "Format: Binary\n" + \
                "Directory: " + self.directory + "\n" + \
                "Experiment Index: " + str(self.experiment_index) + "\n" + \
                "Recording Index: " + str(self.recording_index)
    

    
    
    
    
    
    
    
    
    
    
    
    #####################################################################
    
    @staticmethod
    def detect_format(directory):
        binary_files = glob.glob(os.path.join(directory, 'experiment*', 'recording*'))
        
        if len(binary_files) > 0:
            return True
        else:
            return False
    
    @staticmethod
    def detect_recordings(directory):
        
        recordings = []
        
        experiment_directories = glob.glob(os.path.join(directory, 'experiment*'))
        experiment_directories.sort()

        for experiment_index, experiment_directory in enumerate(experiment_directories):
             
            recording_directories = glob.glob(os.path.join(experiment_directory, 'recording*'))
            recording_directories.sort()
            
            for recording_index, recording_directory in enumerate(recording_directories):
            
                recordings.append(BinaryRecording(recording_directory, 
                                                       experiment_index,
                                                       recording_index))
                
        return recordings
