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

from open_ephys.analysis.Recording import Recording

class NwbRecording(Recording):
    
    class Spikes:
        
        def __init__(self, dataset, channel_count):
            
            timestamps = []
            waveforms = []
            electrodes = []
            
            self.metadata = {}
            
            self.metadata['names'] = list(dataset.keys())
            
            for i, electrode in enumerate(dataset.keys()):
                   
                if dataset[electrode]['data'][()].shape[1] == channel_count:
            
                    timestamps.append(dataset[electrode]['timestamps'][()])
                    waveforms.append(dataset[electrode]['data'][()])
                    electrodes.append(np.array([i] * len(timestamps[-1])))

            self.timestamps = np.concatenate(timestamps)
            self.waveforms = np.concatenate(waveforms, axis=0)
            self.electrodes = np.concatenate(electrodes)
            
            order = np.argsort(self.timestamps)
            
            self.timestamps = self.timestamps[order]
            self.waveforms = self.waveforms[order,:,:]
            self.electrodes = self.electrodes[order]
    
    class Continuous:
        
        def __init__(self, dataset):
            
            self.samples = dataset['data'][()]
            self.timestamps = dataset['timestamps'][()]
    
    def __init__(self, directory, experiment_index, recording_index):
       Recording.__init__(self, directory, experiment_index, recording_index)  
       
    def open_file(self):
        
        return h5.File(os.path.join(self.directory, 'experiment_' + 
                                 str(self.experiment_index+1) + '.nwb'), 'r')
       
    def load_continuous(self):
        
        f = self.open_file()
        
        dataset = f['acquisition']['timeseries']['recording' + 
                                                 str(self.recording_index+1)]['continuous']
        
        self._continuous = [self.Continuous(dataset[processor]) for processor in dataset.keys()]
        
        f.close()
    
    def load_spikes(self):
        
        f = self.open_file()
        
        dataset = f['acquisition']['timeseries']['recording' + str(self.recording_index+1)]['spikes']
        
        spikes = [self.Spikes(dataset, channel_count) for channel_count in (1,2,4)]
        
        self._spikes = [S for S in spikes if len(S.timestamps) > 0]
        
        f.close()
    
    def load_events(self):
        
        f = self.open_file()
        
        dataset = f['acquisition']['timeseries']['recording' + 
                                                 str(self.recording_index+1)]['events']['ttl1']
        
        nodeId = int(dataset.attrs['source'].decode('utf-8').split('_')[1])
        timestamps = dataset['timestamps']
        
        self._events = pd.DataFrame(data = {'channel' : dataset['control'][()],
                              'timestamp' : timestamps,
                              'nodeId' : [nodeId] * len(timestamps),
                              'state' : (np.sign(dataset['data'][()]) + 1 / 2).astype('int')})
        
        f.close()
        
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
                    
            f = h5.File(file, 'r')
            
            for recording_index, r in enumerate(f['acquisition']['timeseries'].keys()):
                
                recordings.append(NwbRecording(directory,
                                                     experiment_index,
                                                     recording_index))
            f.close()
            
        return recordings