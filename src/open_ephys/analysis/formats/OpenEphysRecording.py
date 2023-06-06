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

    class Spikes:
        
        def __init__(self, info, directory, recording_index):
            
            self.metadata = {}
            self.metadata['name'] = info['name']
            self.metadata['stream_name'] = info['stream_name']
            
            self.sample_numbers, self.waveforms, header = \
                load(os.path.join(directory, info['filename']), recording_index)

            self.waveforms = self.waveforms.astype('float64') * info['bit_volts']

            self.metadata['sample_rate'] = float(header['sampleRate'])
            self.metadata['num_channels'] = int(info['num_channels'])

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
            self.sample_range = [self.sample_numbers[0], self.sample_numbers[-1]+1]
            self.selected_channels = np.arange(len(files))

            self.metadata = {}

            self.metadata['source_node_id'] = int(info['source_node_id'])
            self.metadata['source_node_name'] = info['source_node_name']

            self.metadata['stream_name'] = info['stream_name']

            self.metadata['sample_rate'] = info['sample_rate']
            self.metadata['num_channels'] = len(files)

            self.metadata['channel_names'] = info['channel_names']
            self.metadata['bit_volts'] = info['bit_volts']

            self._load_timestamps()

            self.global_timestamps = None

        @property
        def samples(self):
            if self._samples is None or self.reload_required:
                self._load_samples()
                self.reload_required = False
            return self._samples

        def get_samples(self, start_sample_index, end_sample_index, selected_channels=None):
            """
            Returns samples scaled to microvolts. Converts sample values
            from 16-bit integers to 64-bit floats.

            Note: if a subset of data has been loaded, all indices are relative to this
            subset, rather than the original array.
            
            Parameters
            ----------
            start_sample_index : int
                Index of the first sample to return
            end_sample_index : int
                Index of the last sample to return
            selected_channels : numpy.ndarray
                Indices of the channels to return
                By default, all channels are returned

            Returns
            -------
            samples : numpy.ndarray (float64)

            """

            if selected_channels is None:
                selected_channels = np.arange(self.selected_channels.size)

            samples = self.samples[start_sample_index:end_sample_index, selected_channels].astype('float64')

            for idx, channel in enumerate(selected_channels):
                samples[:,idx] = samples[:,idx] * self.metadata['bit_volts'][self.selected_channels[channel]]

            return samples

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

            data = np.memmap(self.timestamps_file, dtype='<f8', offset=0, mode='r')[self.valid_records]
            data = np.append(data, 2 * data[-1] - data[-2])

            self._timestamps_internal = []

            for i in range(len(data)-1):
                self._timestamps_internal.extend(np.linspace(data[i], data[i+1], 1024, endpoint=True))
            
            self.timestamps = self._timestamps_internal

   
            
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

            self._continuous.append(self.Continuous(stream_info[stream_index], 
                            files_for_stream, 
                            self.recording_index))
        
    def load_spikes(self):

        spike_file_info, _, _ = self.find_spikes_files()

        if spike_file_info:
            self._spikes = []
            self._spikes.extend([self.Spikes(info, self.directory, self.recording_index) for info in spike_file_info])
        else:
            self._spikes = None

    
    def load_events(self):
        
        tree = XmlElementTree.parse(self.experiment_info)
        root = tree.getroot()

        events = []
        
        for recording_index, child in enumerate(root):
            if (recording_index == self.recording_index):
                for stream_index, stream in enumerate(child):
                    for file_index, file in enumerate(stream):
                        if file.tag == 'EVENTS':
                            stream_name = file.get('filename').replace('_','.').split('.')[1]
                            sample_number, processor_id, state, channel, header = \
                                load(os.path.join(self.directory, 
                                      file.get('filename')), self.recording_index)
                            events.append(pd.DataFrame(data = {'line' : channel + 1,
                              'sample_number' : sample_number,
                              'processor_id' : processor_id,
                              'stream_index' : [stream_index] * len(sample_number),
                              'stream_name' : [stream_name] * len(sample_number),
                              'state' : state}))

        self._events = pd.concat(events).sort_values(by=['sample_number', 'stream_index'], ignore_index=True)

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
                    info['bit_volts'] = []

                    for file_index, file in enumerate(stream):
                        if file.tag == 'CHANNEL':
                            continuous_files.append(file.get('filename'))
                            info['channel_names'].append(file.get('name'))
                            info['bit_volts'].append(float(file.get('bitVolts')))
                            stream_indexes.append(stream_index)
                        elif file.tag == 'TIMESTAMPS':
                            info['timestamps_file'] = os.path.join(self.directory, file.get('filename'))

                    stream_info.append(info)
        
        return continuous_files, stream_indexes, unique_stream_indexes, stream_info

    def find_spikes_files(self):

        tree = XmlElementTree.parse(self.experiment_info)
        root = tree.getroot()

        spike_file_info = []
        stream_indexes = []
        unique_stream_indexes = []

        for recording_index, child in enumerate(root):
            if (recording_index == self.recording_index):
                for stream_index, stream in enumerate(child):
                    unique_stream_indexes.append(stream_index)
                    for file_index, file in enumerate(stream):
                        if file.tag == 'SPIKECHANNEL':
                            info = {'filename' : file.get('filename'),
                                    'name' : file.get('name'),
                                    'stream_name' : stream.get('name'),
                                    'source_node_id' : int(stream.get('source_node_id')),
                                    'source_node_name' : stream.get('source_node_name'),
                                    'bit_volts' : float(file.get('bitVolts')),
                                    'num_channels' : int(file.get('num_channels'))}
                            spike_file_info.append(info)
                            stream_indexes.append(stream_index)

        return spike_file_info, stream_indexes, unique_stream_indexes
        
        
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