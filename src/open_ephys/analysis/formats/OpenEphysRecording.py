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

from open_ephys.analysis.formats.helpers import load, load_continuous

from open_ephys.analysis.recording import Recording

class OpenEphysRecording(Recording):
    
    class Continuous:
        
        def __init__(self, info, files, recording_index):
            
            self.name = files[0].strip().split('_')[-2]
            self.files = files
            self.timestamps_file = info['timestamps_file']
            self.recording_index = recording_index
            self._sample_numbers_internal, _, _, self.valid_records = load(files[0], recording_index)
            self.global_timestamps = None

            self.reload_required = False
            self._samples = None
            self.sample_numbers = self._sample_numbers_internal
            self.sample_range = [self.sample_numbers[0], self.sample_numbers[-1]]
            self.selected_channels = np.arange(len(files))

            self.metadata = {}

            self.metadata['stream_name'] = info['stream_name']
            self.metadata['source_node_id'] = info['source_node_id']
            self.metadata['source_node_name'] = info['source_node_name']
            self.metadata['sample_rate'] = info['sample_rate']
            self.metadata['channel_names'] = info['channel_names']

            self._load_timestamps()

        @property
        def samples(self):
            if self._samples is None or self.reload_required:
                self._load_samples()
                self.reload_required = False
            return self._samples

        def set_start_sample(self, start_sample):
            """
            Updates start sample and triggers reload next time 
            samples are requested.

            Parameters
            ----------
            start_sample : int
                First sample number (not sample index) to be loaded.
                
            """
            self.sample_range[0] = start_sample
            self.reload_required = True

        def set_end_sample(self, end_sample):
            """
            Updates end sample and triggers reload next time 
            samples are requested.

            Parameters
            ----------
            end_sample : int
                Last sample number (not sample index) to be loaded.
                
            """
            self.sample_range[1] =end_sample
            self.reload_required = True

        def set_sample_range(self, sample_range):
            """
            Updates start and end sample and triggers reload next time 
            samples are requested.

            Parameters
            ----------
            sample_range : 2-element list
                First and last sample numbers (not sample indices) to be loaded.
                
            """
            self.sample_range = sample_range
            self.reload_required = True

        def set_selected_channels(self, selected_channels):
            """
            Updates indices of selected channels and triggers reload next time
            samples are requested.

            Parameters
            ----------
            selected_channels : np.ndarray
                Indices of channels to be loaded.
                
            """
            self.selected_channels = selected_channels
            self.reload_required = True

        def _load_samples(self):

            total_samples = self.sample_range[1] - self.sample_range[0]
            total_channels = len(self.selected_channels)

            self._samples = np.zeros((total_samples, total_channels))

            channel_idx = 0

            for file_idx in self.selected_channels:
                 
                if os.path.splitext(self.files[file_idx])[1] == '.continuous':
                    sample_numbers, samples, _, _ = load_continuous(self.files[file_idx], self.recording_index, self.sample_range[0], self.sample_range[1])
                    
                    self._samples[:,channel_idx] = samples
                    channel_idx += 1

            self.sample_numbers = sample_numbers

            start = np.searchsorted(self._sample_numbers_internal, self.sample_range[0])
            end = np.searchsorted(self._sample_numbers_internal, self.sample_range[1])
            self.timestamps = self._timestamps_internal[start:end]

        def _load_timestamps(self):

            data = np.array(np.memmap(self.timestamps_file, dtype='<f8', offset=0, mode='r'))[self.valid_records]
            data = np.append(data, 2 * data[-1] - data[-2])

            self._timestamps_internal = np.array([])
            for i in range(len(data)-1):
                self._timestamps_internal = np.append(self._timestamps_internal, np.linspace(data[i], data[i+1], 1024, endpoint=True))
            
            self.timestamps = self._timestamps_internal

    class Spikes:
        
        def __init__(self, files, recording_index):
            
            sample_numbers = []
            waveforms = []
            electrodes = []
            
            self.metadata = {}
            self.metadata['names'] = []
            
            for i, file in enumerate(files):
            
                sn, wv, header = load(file, recording_index)
                
                sample_numbers.append(sn)
                waveforms.append(wv)
                electrodes.append(np.array([i] * len(sn)))
                
                self.metadata['names'].append(header['electrode'])
                
            self.sample_numbers = np.concatenate(sample_numbers)
            self.waveforms = np.concatenate(waveforms, axis=0)
            self.electrodes = np.concatenate(electrodes)
            
            order = np.argsort(self.sample_numbers)
            
            self.sample_numbers = self.sample_numbers[order]
            self.waveforms = self.waveforms[order,:,:]
            self.electrodes = self.electrodes[order]

            self.summary = pd.DataFrame(data = {'sample_numbers' : self.sample_numbers,
                    'electrode' : self.electrodes})
            
    def __init__(self, directory, experiment_index=0, recording_index=0):
        
        Recording.__init__(self, directory, experiment_index, recording_index)  
       
        if experiment_index == 0:
            self.experiment_id = ""
        else:
            self.experiment_id = "_" + str(experiment_index+1)

        self.experiment_info = os.path.join(directory, 'structure' + self.experiment_id + '.openephys')

        if not os.path.exists(self.experiment_info):
            self.experiment_info = os.path.join(directory, 'Continuous_Data' + self.experiment_id + '.openephys')
           
        self._format = 'open-ephys'
       
    def load_continuous(self):
        
        continuous_files, stream_indexes, unique_stream_indexes, stream_info = \
            self.find_continuous_files()
        self._continuous = []

        for stream_index in unique_stream_indexes:

            files_for_stream = [ ]
            for ind, filename in enumerate(continuous_files):
                if stream_indexes[ind] == stream_index:
                    files_for_stream.append(os.path.join(self.directory, filename))

            print(stream_info)

            self._continuous.append(self.Continuous(stream_info[stream_index], 
                            files_for_stream, 
                            self.recording_index))
        
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
                            sample_number, processor_id, state, channel, header = \
                                load(os.path.join(self.directory, 
                                      file.get('filename')), self.recording_index)
                            events.append(pd.DataFrame(data = {'line' : channel + 1,
                              'sample_number' : sample_number,
                              'processor_id' : processor_id,
                              'stream_index' : [stream_index] * len(sample_number),
                              'state' : state}))

        self._events = pd.concat(events).sort_values(by='sample_number')

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

                    info['stream_name'] = stream.get('name')
                    info['source_node_id'] = stream.get('source_node_id')
                    info['source_node_name'] = stream.get('source_node_name')
                    info['sample_rate'] = float(stream.get('sample_rate'))
                    info['channel_names'] = []

                    for file_index, file in enumerate(stream):
                        if file.tag == 'CHANNEL':
                            continuous_files.append(file.get('filename'))
                            info['channel_names'].append(file.get('name'))
                            stream_indexes.append(stream_index)
                        elif file.tag == 'TIMESTAMPS':
                            info['timestamps_file'] = os.path.join(self.directory, file.get('filename'))

                    stream_info.append(info)
        
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

    @staticmethod
    def create_openephys_file(
        output_path, 
        stream_name="example_data",
        channel_count=16,
        sample_rate=30000.,
        bit_volts=0.195):

        """
        Generates structure.openephys (XML) file for one data stream

        A minimal directory structure for the Open Ephys format looks 
        like this:

        data-directory/
            *.continuous files
            *.events files
            *.spikes files 
            *.timestamps files
            structure.openephys

        Parameters
        ----------
        output_path : string
            directory in which to write the file (structure.oebin will
            be added automatically)
        stream_name : string
            name of the data stream that generated the data
        channel_count : int
            number of .continuous files
        sample_rate : float
            samples rate of the .continuous files
        bit_volts : float
            scaling factor required to convert int16 values in to µV
        
        """

        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom

        experiment = Element("EXPERIMENT")
        experiment.attrib = {"format_version" : "0.6",
                            "number" : "1"}

        source_node_id = 100

        recording = SubElement(experiment, "RECORDING")
        recording.attrib = {"number" : "1"}

        stream = SubElement(recording, "STREAM")
        stream.attrib = {"name" : stream_name,
                        "sample_rate" : str(sample_rate),
                        "source_node_id" : str(source_node_id)}

        prefix = "_".join([str(source_node_id), stream_name])

        for i in range(channel_count):
            channel = SubElement(stream, "CHANNEL")
            name = "CH" + str(i+1)
            channel.attrib = {"name" : name,
                            "bitVolts" : str(bit_volts),
                            "filename" : "_".join([prefix,name + '.continuous']),
                            "position" : "1024.0"}
            
        events = SubElement(stream, "EVENTS")
        events.attrib = {"filename" : prefix + ".events"}

        timestamps = SubElement(stream, "TIMESTAMPS")
        timestamps.attrib = {"filename" : prefix + ".timestamps"}
            
        dom = minidom.parseString(tostring(experiment))

        with open(os.path.join(output_path, "structure.openephys"), 'wb') as f:
            f.write(dom.toprettyxml(indent='  ', encoding="UTF-8"))
            f.close()