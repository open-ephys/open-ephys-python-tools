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
import pandas as pd
import numpy as np

import xml.etree.ElementTree as ET

from open_ephys.analysis.formats.helpers import load

from open_ephys.analysis.recording import Recording

class OpenEphysRecording(Recording):
    
    class Continuous:
        
        def __init__(self, files, processor_id, recording_index):
            
            files = [file for file in files if os.path.basename(file).split('_')[0] == processor_id]
            
            self.timestamps, _, _ = load(files[0], recording_index)
            
            self.samples = np.zeros((len(self.timestamps), len(files)))
            self.metadata = {}
            self.metadata['names'] = []
            self.metadata['processor_id'] = processor_id
            
            for file_idx, file in enumerate(files):
                
                try:
                    channel_number = int(os.path.basename(file).split('_')[1].split('.')[0].split('H')[1])
                except IndexError:
                    channel_number = int(os.path.basename(file).split('_')[1].split('.')[0]) - 1
                
                timestamps, samples, header = load(file, recording_index)

                self.samples[:,channel_number] = samples
            
    class Spikes:
        
        def __init__(self, files, recording_index):
            
            timestamps = []
            waveforms = []
            electrodes = []
            
            self.metadata = {}
            self.metadata['names'] = []
            
            for i, file in enumerate(files):
            
                ts, wv, header = load(file, recording_index)
                
                timestamps.append(ts)
                waveforms.append(wv)
                electrodes.append(np.array([i] * len(ts)))
                
                self.metadata['names'].append(header['electrode'])
                
            self.timestamps = np.concatenate(timestamps)
            self.waveforms = np.concatenate(waveforms, axis=0)
            self.electrodes = np.concatenate(electrodes)
            
            order = np.argsort(self.timestamps)
            
            self.timestamps = self.timestamps[order]
            self.waveforms = self.waveforms[order,:,:]
            self.electrodes = self.electrodes[order]
            
    def __init__(self, directory, experiment_index, recording_index):
       Recording.__init__(self, directory, experiment_index, recording_index)  
       
       if experiment_index == 0:
           self.experiment_id = ""
       else:
           self.experiment_id = "_" + str(experiment_index+1)
       
    def load_continuous(self):
        
        files = self.find_continuous_files()
        
        processor_ids = np.unique(np.array([os.path.basename(fname).split('_')[0]
                                            for fname in files]))
        
        self._continuous = [self.Continuous(files, processor_id, self.recording_index)
                            for processor_id in processor_ids]
        
    def load_spikes(self):
        
        self._spikes = [self.Spikes(self.find_spikes_files(file_type), 
                                    self.recording_index)
                        for file_type in ('single electrode','stereotrode', 'tetrode')
                        if len(self.find_spikes_files(file_type)) > 0]
    
    def load_events(self):
        
        events_file = os.path.join(self.directory, 'all_channels' + self.experiment_id + ".events")
        
        timestamps, processor_id, state, channel, header = load(events_file, self.recording_index)
        
        self._events = pd.DataFrame(data = {'channel' : channel + 1,
                              'timestamp' : timestamps,
                              'nodeId' : processor_id,
                              'state' : state})

    def find_continuous_files(self):
    
        f = glob.glob(os.path.join(self.directory, '*continuous'))
        f.sort()
        
        experiment_ids = [os.path.basename(name).split('_')[1] for name in f]
        
        experiment1_files = []
        experimentN_files = []
        
        for idx, name in enumerate(f):
            
            if experiment_ids[idx].find('continuous') > 0:
                experiment1_files.append(name)
            else:
                experimentN_files.append(name)

        if self.experiment_index == 0:
            return experiment1_files
        else:
            return [name for name in experimentN_files 
                    if (os.path.basename(name).split('_')[2].split('.')[0] == str(self.experiment_index + 1))]
        
    def find_spikes_files(self, file_type):
    
        search_string = {'single electrode' : 'SE',
                         'stereotrode': 'ST',
                         'tetrode': 'TT'}    
    
        if self.experiment_index == 0:
            f = glob.glob(os.path.join(self.directory, 
                                       search_string[file_type] + '*spikes'))
            f.sort()
            return [name for name in f 
                    if (os.path.basename(name).find('_') < 0)]
        else:
            f = glob.glob(os.path.join(self.directory, search_string[file_type] + 
                                                       '*' + self.experiment_id + '*spikes'))
            f.sort()
            return [name for name in f 
                    if (os.path.basename(name).split('_')[1].split('.')[0] == str(self.experiment_index + 1))]
        
        
    def __str__(self):
        """Returns a string with information about the Recording"""
        
        return "Open Ephys GUI Recording\n" + \
                "ID: " + hex(id(self)) + '\n' + \
                "Format: Open Ephys\n" + \
                "Directory: " + self.directory + "\n" + \
                "Experiment Index: " + str(self.experiment_index) + "\n" + \
                "Recording Index: " + str(self.recording_index)
                
        # %%
    
    
    
    
    
    
    
    
    
    
    
    
    
    ###############################################################
    
    @staticmethod
    def detect_format(directory):
        open_ephys_files = glob.glob(os.path.join(directory, '*.events'))

        if len(open_ephys_files) > 0:
            return True
        else:
            return False
    
    @staticmethod
    def detect_recordings(directory):
        
        recordings = []
        
        message_files = glob.glob(os.path.join(directory, 'messages*events'))
        message_files.sort()
        
        for experiment_index, message_file in enumerate(message_files):
             
            if experiment_index == 0:
                experiment_id = ""
            else:
                experiment_id = "_" + str(experiment_index + 1)
                
            continuous_info = glob.glob(os.path.join(directory, 'Continuous_Data' 
                                                     + experiment_id 
                                                     + '.openephys'))
            
            found_recording = False
            
            if len(continuous_info) > 0:
                tree = ET.parse(continuous_info[0])
                root = tree.getroot()
                for recording_index, child in enumerate(root):
                    recordings.append(OpenEphysRecording(directory, 
                                                       experiment_index,
                                                       recording_index))
                found_recording = True
                
            if not found_recording:
                event_file = glob.glob(os.path.join(directory, 'all_channels' + experiment_id + '.events'))
                
                if len(event_file) > 0:
                    
                    events = loadEvents(event_file[0])
                    
                    for recording_index in np.unique(events['recordingNumber']):
                        
                        recordings.append(OpenEphysRecording(directory, 
                                                           experiment_index,
                                                           recording_index))
                    
                    found_recording = True
                    
            if not found_recording:
                spikes_files = glob.glob(os.path.join(directory, '*n[0-9]' + experiment_id + '.spikes'))
                
                if len(spikes_files) > 0:
                    
                    spikes = loadSpikes(spikes_files[0])
                    
                    for recording_index in np.unique(spikes['recordingNumber']):
                        
                        recordings.append(OpenEphysRecording(directory, 
                                                           experiment_index,
                                                           recording_index))
                        
                    found_recording = True
                
            if not found_recording:
                raise(IOError('Could not find any data files.'))
                
        return recordings