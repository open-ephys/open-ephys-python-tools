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

import xml.etree.ElementTree as XmlElementTree

from open_ephys.analysis.formats.helpers import load

from open_ephys.analysis.recording import Recording

class OpenEphysRecording(Recording):
    
    class Continuous:
        
        def __init__(self, info, files, recording_index):
            
            self.name = files[0].strip().split('_')[-2]
            self.sample_numbers, _, _, self.valid_records = load(files[0], recording_index)
            self.global_timestamps = None
            
            self.samples = np.zeros((len(self.sample_numbers), len(files)-1))

            self.metadata = {}

            self.metadata['name'] = info['name']
            self.metadata['source_node_id'] = info['source_node_id']
            self.metadata['source_node_name'] = info['source_node_name']
            self.metadata['sample_rate'] = info['sample_rate']
            
            for file_idx, file in enumerate(files):
                 
                if os.path.splitext(file)[1] == '.continuous':
                    _, samples, _, _ = load(file, recording_index)
                    self.samples[:,file_idx] = samples
                else:
                    self.timestamps_file = file

            self.load_timestamps()

        def load_timestamps(self):

            data = np.array(np.memmap(self.timestamps_file, dtype='<f8', offset=0, mode='r'))[self.valid_records]
            data = np.append(data, 2 * data[-1] - data[-2])

            self.timestamps = np.array([])
            for i in range(len(data)-1):
                self.timestamps = np.append(self.timestamps, np.linspace(data[i], data[i+1], 1024, endpoint=True))
                
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

            self.summary = pd.DataFrame(data = {'timestamp' : self.timestamps,
                    'electrode' : self.electrodes})
            
    def __init__(self, directory, experiment_index=0, recording_index=0):
        
        Recording.__init__(self, directory, experiment_index, recording_index)  
       
        if experiment_index == 0:
            self.experiment_id = ""
        else:
            self.experiment_id = "_" + str(experiment_index+1)

        self.experiment_info = os.path.join(directory, 'structure' + self.experiment_id + '.openephys')
           
        self._format = 'open-ephys'
       
    def load_continuous(self):
        
        files, stream_inds, unique_stream_inds, stream_info = self.find_continuous_files()
        self._continuous = []

        for stream_index in unique_stream_inds:

            files_for_stream = [ ]
            for ind, filename in enumerate(files):
                if stream_inds[ind] == stream_index:
                    files_for_stream.append(os.path.join(self.directory, filename))

            self._continuous.append(self.Continuous(stream_info[stream_index], files_for_stream, self.recording_index))
        
    def load_spikes(self):

        spike_files, _, _ = self.find_spikes_files()

        if spike_files:
            spike_files = [os.path.join(self.directory, filename) for filename in spike_files]
            self._spikes = self.Spikes(spike_files, self.recording_index)
        else:
            self._spikes = None

        '''
        for file_type in ('single electrode','stereotrode', 'tetrode'):
            print("***Found {} {} ".format(len(self.find_spikes_files(file_type)), file_type))
        
        self._spikes = [self.Spikes(self.find_spikes_files(file_type), 
                                    self.recording_index)
                        for file_type in ('single electrode','stereotrode', 'tetrode')
                        if len(self.find_spikes_files(file_type)) > 0]
        '''
    
    def load_events(self):
        
        tree = XmlElementTree.parse(self.experiment_info)
        root = tree.getroot()

        events = []
        
        for recording_index, child in enumerate(root):
            if (recording_index == self.recording_index):
                for stream_index, stream in enumerate(child):
                    for file_index, file in enumerate(stream):
                        if file.tag == 'EVENTS':
                            timestamps, processor_id, state, channel, header = \
                                load(os.path.join(self.directory, 
                                      file.get('filename')), self.recording_index)
                            events.append(pd.DataFrame(data = {'line' : channel + 1,
                              'timestamp' : timestamps,
                              'processor_id' : processor_id,
                              'stream_index' : [stream_index] * len(timestamps),
                              'state' : state}))

        self._events = pd.concat(events).sort_values(by='timestamp')

    def load_messages(self):
        
        if len(self.experiment_id) == 0:
            messages_file = os.path.join(self.directory, 'messages' + '.events')
        else:
            messages_file = os.path.join(self.directory, 'messages_' + str(self.experiment_id) + '.events')

        df = pd.read_csv(messages_file, header=None, names=['timestamp', 'message'])
        splits = np.where(df.message == ' Software Time (milliseconds since midnight Jan 1st 1970 UTC)')[0]
        splits = np.concatenate((splits, np.array([len(df)])))

        self._messages = df.iloc[splits[self.recording_index]+1:splits[self.recording_index+1]]

    def find_continuous_files(self):
    
        tree = XmlElementTree.parse(self.experiment_info)
        root = tree.getroot()

        continuous_files = []
        stream_indexes = []
        unique_stream_indexes = []
        stream_info = []
        
        for recording_index, child in enumerate(root):
            if (recording_index == self.recording_index):
                for stream_index, stream in enumerate(child):
                    unique_stream_indexes.append(stream_index)

                    info = {}

                    info['name'] = stream.get('name')
                    info['source_node_id'] = stream.get('source_node_id')
                    info['source_node_name'] = stream.get('source_node_name')
                    info['sample_rate'] = float(stream.get('sample_rate'))

                    stream_info.append(info)

                    for file_index, file in enumerate(stream):
                        if file.tag in ('CHANNEL', 'TIMESTAMPS'):
                            continuous_files.append(file.get('filename'))
                            stream_indexes.append(stream_index)
                        elif file.tag == 'TIMESTAMPS':
                            timestamps_file = file.get('filename')
        
        return continuous_files, stream_indexes, unique_stream_indexes, stream_info

    def find_spikes_files(self):

        tree = XmlElementTree.parse(self.experiment_info)
        root = tree.getroot()

        spike_files = []
        stream_indexes = []
        unique_stream_indexes = []

        for recording_index, child in enumerate(root):
            if (recording_index == self.recording_index):
                for stream_index, stream in enumerate(child):
                    unique_stream_indexes.append(stream_index)
                    for file_index, file in enumerate(stream):
                        if file.tag == 'SPIKECHANNEL':
                            spike_files.append(file.get('filename'))
                            stream_indexes.append(stream_index)

        return spike_files, stream_indexes, unique_stream_indexes
    
        '''
        search_string = {'single electrode' : 'Electrode',
                         'stereotrode': 'Stereotrode',
                         'tetrode': 'Tetrode'}    
    
        if self.experiment_index == 0:
            print((os.path.join(self.directory, 
                                       search_string[file_type] + '*spikes')))
            f = glob.glob(os.path.join(self.directory, 
                                       search_string[file_type] + '*spikes'))
            print("Got spike files: {}".format(f))
            f.sort()
            return [name for name in f 
                    if True]#(os.path.basename(name).find('_') < 0)]
        else:
            f = glob.glob(os.path.join(self.directory, search_string[file_type] + 
                                                       '*' + self.experiment_id + '*spikes'))
            f.sort()
            return [name for name in f 
                    if (os.path.basename(name).split('_')[1].split('.')[0] == str(self.experiment_index + 1))]
        '''
        
        
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
        
        experiment_info = glob.glob(os.path.join(directory, 'structure*.openephys'))
        experiment_info.sort()

        for experiment_index, file_name in enumerate(experiment_info):

            tree = XmlElementTree.parse(file_name)
            root = tree.getroot()
            for recording_index, child in enumerate(root):
                recordings.append(OpenEphysRecording(directory, 
                                                    experiment_index,
                                                    recording_index))
                
        return recordings