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

import h5py as h5
import glob
import os
import numpy as np
import pandas as pd

from open_ephys.analysis.recording import Recording

class KwikRecording(Recording):
    
    class Spikes:
        
        def __init__(self, dataset, channel_count, recording_index):
            
            timestamps = []
            waveforms = []
            electrodes = []
            
            self.metadata = {}
            self.metadata['names'] = list(dataset.keys())
            
            for i, electrode in enumerate(dataset.keys()):
                
                if dataset[electrode]['waveforms_filtered'].shape[2] == channel_count:
            
                    mask = dataset[electrode]['recordings'][()] == recording_index
                
                    timestamps.append(dataset[electrode]['time_samples'][()][mask])
                    waveforms.append(np.swapaxes(dataset[electrode]['waveforms_filtered'][()][mask,:,:],1,2))
                    electrodes.append(np.array([i] * len(timestamps[-1])))

            self.timestamps = np.concatenate(timestamps)
            self.waveforms = np.concatenate(waveforms, axis=0)
            self.electrodes = np.concatenate(electrodes)
            
            order = np.argsort(self.timestamps)
            
            self.timestamps = self.timestamps[order]
            self.waveforms = self.waveforms[order,:,:]
            self.electrodes = self.electrodes[order]
    
    class Continuous:
        
        def __init__(self, file, recording_index):
            
            f = h5.File(file, 'r')
            
            dataset = f['recordings'][str(recording_index)]
            
            self.samples = dataset['data'][()]
            
            start_time = dataset['application_data']['timestamps'][()][0][0]

            self.timestamps = np.arange(start_time, start_time + self.samples.shape[0])
            
            f.close()
    
    def __init__(self, directory, experiment_index, recording_index):
       Recording.__init__(self, directory, experiment_index, recording_index)  
       
    def load_continuous(self):
        
        kwd_files = glob.glob(os.path.join(self.directory, 'experiment' +
                                           str(self.experiment_index + 1) + '*.kwd'))
            
        if len(kwd_files) > 0:
            
            self._continuous = [self.Continuous(file, self.recording_index) for file in kwd_files]
            
        
    def load_spikes(self):
        
        spikes_file = os.path.join(self.directory, 'experiment' + str(self.experiment_index + 1) + '.kwx')
        
        f = h5.File(spikes_file, 'r')
        
        electrodes = f['channel_groups']
        
        spikes = [self.Spikes(electrodes, channel_count, self.recording_index) for channel_count in (1,2,4)]
        
        self._spikes = [S for S in spikes if len(S.timestamps) > 0]
            
        f.close()
    
    def load_events(self):
        
        events_file = os.path.join(self.directory, 'experiment' + str(self.experiment_index + 1) + '.kwe')
        
        f = h5.File(events_file, 'r')
        
        recordings = f['event_types']['TTL']['events']['recording'][()]
        timestamps = f['event_types']['TTL']['events']['time_samples'][()]
        
        mask = recordings == self.recording_index
        
        dataset = f['event_types']['TTL']['events']['user_data']
        
        self._events = pd.DataFrame(data = {'channel' : dataset['event_channels'][()][mask] + 1,
                              'timestamp' : timestamps[mask],
                              'nodeId' : dataset['nodeID'][()][mask],
                              'state' : dataset['eventID'][mask].astype('int')})
        
        f.close()
        
    def __str__(self):
        """Returns a string with information about the Recording"""
        
        return "Open Ephys GUI Recording\n" + \
                "ID: " + hex(id(self)) + '\n' + \
                "Format: Kwik\n" + \
                "Directory: " + self.directory + "\n" + \
                "Experiment Index: " + str(self.experiment_index) + "\n" + \
                "Recording Index: " + str(self.recording_index)
        

    
    
    ########################################################
        
    @staticmethod
    def detect_format(directory):
        kwik_files = glob.glob(os.path.join(directory, '*.kw*'))

        if len(kwik_files) > 0:
            return True
        else:
            return False
        
    @staticmethod
    def detect_recordings(directory):
        
        recordings = []
        
        found_recording = False
                    
        kwe_files = glob.glob(os.path.join(directory, 'experiment*.kwe'))
        kwe_files.sort()
        
        if len(kwe_files) > 0:
            
            for experiment_index, file in enumerate(kwe_files):
                print(file)
                
                f = h5.File(file, 'r')
                
                for recording_index, r in enumerate(f['recordings'].keys()):
                    
                    recordings.append(KwikRecording(directory,
                                                         experiment_index,
                                                         recording_index))
                    
                f.close()
                    
            found_recording = True
            
        if not found_recording:
            
            kwd_files = glob.glob(os.path.join(directory, 'experiment*.kwd'))
            kwd_files.sort()
            
            if len(kwd_files) > 0:
                
                for experiment_index, file in enumerate(kwd_files):
                    
                    f = h5.File(file, 'r')
                    
                    for recording_index, r in enumerate(f['recordings'].keys()):
                        
                        recordings.append(KwikRecording(directory,
                                                             experiment_index,
                                                             recording_index))
                        
                    f.close()
                        
                found_recording = True
                
        if not found_recording:
            
            kwx_files = glob.glob(os.path.join(directory, 'experiment*.kwx'))
            kwx_files.sort()
            
            if len(kwx_files) > 0:
                
                for experiment_index, file in enumerate(kwx_files):
                    
                    f = h5.File(file, 'r')
                    
                    for recording_index, r in enumerate(f['recordings'].keys()):
                        
                        recordings.append(KwikRecording(directory,
                                                             experiment_index,
                                                             recording_index))
                        
                    f.close()
                        
                found_recording = True
                
                
        if not found_recording:
            raise(IOError('Could not find any data files.'))
            
        return recordings