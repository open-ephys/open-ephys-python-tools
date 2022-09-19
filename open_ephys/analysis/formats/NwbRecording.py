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
import h5py as h5

import numpy as np
import pandas as pd

from open_ephys.analysis.recording import Recording

class NwbRecording(Recording):
    
    class Spikes:
        
        def __init__(self, nwb, dataset):
        
            self.metadata = {}
            self.metadata['name'] = dataset
            self.metadata['channel_count'] = nwb['acquisition'][dataset]['data'][()].shape[1]

            self.timestamps = nwb['acquisition'][dataset]['timestamps'][()]
            self.waveforms = nwb['acquisition'][dataset]['data'][()]
    
    class Continuous:
        
        def __init__(self, nwb, dataset):

            self.metadata = {}
            self.metadata['name'] = dataset
            
            self.samples = nwb['acquisition'][dataset]['data'][()]
            self.sample_numbers = nwb['acquisition'][dataset]['sync'][()]
            self.timestamps = nwb['acquisition'][dataset]['timestamps'][()]
            
    def __init__(self, directory, experiment_index=0, recording_index=0):
        
       Recording.__init__(self, directory, experiment_index, recording_index)  
       self._format = 'nwb'
       self.nwb = h5.File(os.path.join(self.directory, 'experiment' + 
                                 str(self.experiment_index+1) + '.nwb'), 'r')
    
    def __delete__(self):

        self.nwb.close()
       
    def load_continuous(self):
        
        datasets = list(self.nwb['acquisition'].keys())

        self._continuous = [self.Continuous(self.nwb, dataset) for dataset in datasets
                            if self.nwb['acquisition'][dataset].attrs['neurodata_type'] == 'ElectricalSeries']
    
    def load_spikes(self):
        
        datasets = list(self.nwb['acquisition'].keys())   

        self._spikes = [self.Spikes(self.nwb, dataset) for dataset in datasets
                         if self.nwb['acquisition'][dataset].attrs['neurodata_type'] == 'SpikeEventSeries']

    def load_events(self):
         
        datasets = list(self.nwb['acquisition'].keys())   

        events = []
        processor_ids = []
        
        for dataset in datasets:
            
            if (dataset[-4:] == '.TTL'):

                processor_id = int(dataset.split('.')[0].split('-')[1])

                if processor_id not in processor_ids:
                    processor_ids.append(processor_id)
                    stream_id = 0
                else:
                    stream_id += 1
                
                ds = self.nwb['acquisition'][dataset]
                channel_states = ds['data'][()]
                sample_numbers = ds['sync'][()]
                timestamps = ds['timestamps'][()]
                
                events.append(pd.DataFrame(
                    data = {'line' : np.abs(channel_states),
                            'timestamp' : timestamps,
                            'sample_number' : sample_numbers,
                            'processor_id' : [processor_id] * len(channel_states),
                            'stream_index' : [stream_id] * len(channel_states),
                            'state' : (np.sign(channel_states) + 1 / 2).astype('int')}))
        
        self._events = pd.concat(events)
        self._events.sort_values(by='timestamp')

    def load_messages(self):
        pass
        
    def __str__(self):
        """Returns a string with information about the Recording"""
        
        return "Open Ephys GUI Recording\n" + \
                "ID: " + hex(id(self)) + '\n' + \
                "Format: NWB 1.0\n" + \
                "Directory: " + self.directory + "\n" + \
                "Experiment Index: " + str(self.experiment_index) + "\n" + \
                "Recording Index: " + str(self.recording_index)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    ###############################################################
        
    @staticmethod
    def detect_format(directory):
        nwb_files = glob.glob(os.path.join(directory, '*.nwb'))

        if len(nwb_files) > 0:
            return True
        else:
            return False
    
    @staticmethod
    def detect_recordings(directory):
        
        recordings = []
        
        found_recording = False
                    
        nwb_files = glob.glob(os.path.join(directory, 'experiment*.nwb'))
        nwb_files.sort()
        
        for experiment_index, file in enumerate(nwb_files):

            try:      
                f = h5.File(file, 'r')
            except BlockingIOError:
                print("Error: " + file + "\nis likely still in use. Try closing the GUI and re-loading the session object.")
            else:
                recordings.append(NwbRecording(directory,
                                                        experiment_index,
                                                        0))
                f.close()
            
        return recordings