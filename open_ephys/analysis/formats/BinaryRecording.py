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
        
            directory = os.path.join(base_directory, 'spikes', info['folder_name'])
            
            self.timestamps = np.load(os.path.join(directory, 'spike_times.npy'))
            self.electrodes = np.load(os.path.join(directory, 'spike_electrode_indices.npy')) - 1
        
            self.waveforms = np.load(os.path.join(directory, 'spike_waveforms.npy'))
            
            if self.waveforms.ndim == 2:
                self.waveforms = np.expand_dims(self.waveforms, 1)
    
    class Continuous:
        
        def __init__(self, info, base_directory):
            
            directory = os.path.join(base_directory, 'continuous', info['folder_name'])

            self.metadata = {}
            self.metadata['sample_rate'] = info['sample_rate']
            self.metadata['num_channels'] = info['num_channels']
            self.metadata['processor_id'] = info['source_processor_id']
            self.metadata['subprocessor_id'] = info['source_processor_sub_idx']
            self.metadata['names'] = [ch['channel_name'] for ch in info['channels']]
            
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
                                    'TTL_*')
        
    
        events_directories = glob.glob(search_string)
        
        df = []
        
        for events_directory in events_directories:
            
            node_name = os.path.basename(os.path.dirname(events_directory))
            nodeId = int(node_name.split('-')[-1].split('.')[0])
            subProcessorId = int(node_name.split('-')[-1].split('.')[1])
            
            channels = np.load(os.path.join(events_directory, 'channels.npy'))
            timestamps = np.load(os.path.join(events_directory, 'timestamps.npy'))
            channel_states = np.load(os.path.join(events_directory, 'channel_states.npy'))
        
            df.append(pd.DataFrame(data = {'channel' : channels,
                              'timestamp' : timestamps,
                              'processor_id' : [nodeId] * len(channels),
                              'subprocessor_id' : [subProcessorId] * len(channels),
                              'state' : (channel_states / channels + 1 / 2).astype('int')}))
            
        
            
        if len(df) > 0:
                                               
            self._events = pd.concat(df).sort_values(by='timestamp', ignore_index=True)

        else:
            
            self._events = None
    

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
