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

import os
import numpy as np

NUM_HEADER_BYTES = 1024
SAMPLES_PER_RECORD = 1024
BYTES_PER_SAMPLE = 2
RECORD_MARKER = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 255])
RECORD_SIZE = 4 + 8 + SAMPLES_PER_RECORD * BYTES_PER_SAMPLE + len(RECORD_MARKER) # size of each continuous record in bytes
EVENT_RECORD_SIZE = 32


def readHeader(filename):
    
    """
    Reads in the header of an Open Ephys data file.
    
    Input:
    =====
    filename - string
        path to the data file (.spikes, .events, or .continuous)
    
    """
    
    f = open(filename,'rb')
    
    header = { }
    h = f.read(NUM_HEADER_BYTES).decode().replace('\n','').replace('header.','')
    for i,item in enumerate(h.split(';')):
        if '=' in item:
            header[item.split(' = ')[0]] = item.split(' = ')[1]
            
    return header


def getNumRecords(filename, record_size):
    
    """
    Calculates the number of records in a file, for a given record size
    
    Fails if the file size is not evenly divisible by the record size
    
    Input:
    =====
    filename - string
        path to the data file (.spikes, .events, or .continuous)
    
    record_size - int
        record size in bytes
    
    """
    
    f = open(filename,'rb')
            
    numRecords = (os.fstat(f.fileno()).st_size - NUM_HEADER_BYTES) / record_size
    
    assert numRecords % 1 == 0
            
    return int(numRecords)



def load(filename, recording_index):
    
    """
    Checks file extension, and loads data using the appropriate method
    
    Input:
    =====
    filename - string
        path to the data file (.spikes, .events, or .continuous)
    
    recording_index - int
        index of the recording (0, 1, 2, etc.)
    
    """
    
    extension = os.path.basename(filename).split('.')[-1]

    if extension == 'continuous':
        
        return load_continuous(filename, recording_index)
        
    elif extension == 'spikes':
        
        return load_spikes(filename, recording_index)
        
    elif extension == 'events':
        
        return load_events(filename, recording_index)

    else:
        raise Exception("File extension " + extension + " not recognized")

def load_continuous(filename, recording_index, start_sample=None, end_sample=None):
    
    """
    Loads continuous data, using memory mapping to improve performance
    
    The returned data is not memory mapped
    
    Input:
    =====
    filename - string
        path to the data file (.spikes, .events, or .continuous)
    
    recording_index - int
        index of the recording (0, 1, 2, etc.)

    start_sample - int
        first sample to load (if None, load from the beginning of the recording)

    end_sample - int
        last sample to load (if None, load until the end of the recording)
        
    Output:
    ======
    sample_numbers - np.array (N x 0)
        Sample numbers for each of N data samples
    
    samples - np.array (N x M)
        Samples for each of M channels
    
    header - dict
        Information from file header
    
    """
    
    numRecords = getNumRecords(filename, RECORD_SIZE)
    
    header = readHeader(filename)
    
    data = np.memmap(filename, mode='r', dtype='>i2', 
                 shape = (numRecords, RECORD_SIZE//2), 
                 offset = 1024)

    valid_records = data[:,5] == recording_index * 256
    
    sample_mask = np.zeros((RECORD_SIZE//2,), dtype='bool')
    sample_mask[6:-5] = 1
    sample_mask = np.tile(sample_mask, (data.shape[0],1))
    
    record_mask = np.zeros(data.shape, dtype='bool')
    record_mask[valid_records,:] = 1
    
    mask = record_mask * sample_mask
    
    first_record = np.min(np.where(valid_records)[0])
    
    samples = data.flatten()[mask.flatten()]
    
    f = open(filename,'rb')
    start_sample_number = np.fromfile(f, np.dtype('<i8'), count = 1, offset=1024 + first_record * RECORD_SIZE) # little-
    
    sample_numbers = np.arange(start_sample_number, start_sample_number + samples.size)

    if start_sample is not None:
        start = np.searchsorted(sample_numbers, start_sample)
    else:
        start = 0
    
    if end_sample is not None:
        end = np.searchsorted(sample_numbers, end_sample)
    else:
        end = len(sample_numbers)

    return sample_numbers[start:end], samples[start:end], header, valid_records


def load_events(filename, recording_index):
    
    """
    Loads event data, using memory mapping to improve performance
    
    The returned data is not memory mapped
    
    Input:
    =====
    filename - string
        path to the data file (.spikes, .events, or .continuous)
    
    recording_index - int
        index of the recording (0, 1, 2, etc.)
        
    Output:
    ======
    sample_numbers - np.array (N x 0)
        Sample numbers for each of N events
    
    processor_id - np.array (N x 0)
        Processor ID for each of N events
    
    state - np.array (N x 0)
        State for each of N events (1 = ON, 0 = OFF)
        
    channel - np.array (N x 0)
        Channel index for each of N events
    
    header - dict
        Information from file header
    
    """
    
    header = readHeader(filename)

    sample_numbers = np.array(np.memmap(filename, dtype='<i8', offset=1024, mode='r')[::2])
    
    data = np.memmap(filename, dtype='<u1', offset=1024, mode='r', shape=(len(sample_numbers), EVENT_RECORD_SIZE //2))
    
    recording_number = np.array(data[:,14])
    
    mask = recording_number == recording_index
    processor_id = np.array(data[mask,11])
    state = np.array(data[mask,12])
    channel = np.array(data[mask,13])
    
    return sample_numbers[mask], processor_id, state, channel, header


def load_spikes(filename, recording_number):
    
    """
    Loads spike data, using memory mapping to improve performance
    
    The returned data is not memory mapped
    
    Input:
    =====
    filename - string
        path to the data file (.spikes, .events, or .continuous)
    
    recording_index - int
        index of the recording (0, 1, 2, etc.)
        
    Output:
    ======
    sample_numbers - np.array (N x 0)
        Sample numbers for each of N spikes
    
    waveforms - np.array (N x channels x samples)
        Waveforms for each spike
    
    header - dict
        Information from file header
    
    """
    
    header = readHeader(filename)
    
    f = open(filename, 'rb')
    numChannels = np.fromfile(f, np.dtype('<u2'), 1, offset=1043)[0] 
    numSamples = np.fromfile(f, np.dtype('<u2'), 1)[0] # can be 0, ideally 40 (divisible by 8)
    
    SPIKE_RECORD_SIZE = 42 + \
                        2 * numChannels * numSamples + \
                        4 * numChannels + \
                        2 * numChannels + 2
                        
    POST_BYTES = 4 * numChannels + \
                 2 * numChannels + 2

    NUM_HEADER_BYTES = 1024
    
    f = open(filename,'rb')
    numSpikes = (os.fstat(f.fileno()).st_size - NUM_HEADER_BYTES) // SPIKE_RECORD_SIZE

    sample_numbers = np.zeros((numSpikes,), dtype='<i8')
    
    f.seek(NUM_HEADER_BYTES + 1)
    
    for i in range(len(sample_numbers)):
        
        sample_numbers[i] = np.fromfile(f, np.dtype('<i8'), 1)
        f.seek(NUM_HEADER_BYTES + 1 + SPIKE_RECORD_SIZE * i)
    

    data = np.memmap(filename, mode='r', dtype='<u2', 
                     shape = (numSpikes, SPIKE_RECORD_SIZE//2), 
                     offset = NUM_HEADER_BYTES) 
    
    mask = data[:,-1] == recording_number

    sample_numbers = np.copy(sample_numbers[mask])
 
    waveforms = np.copy(data[mask, 21:-POST_BYTES//2].reshape((np.sum(mask), numChannels, numSamples))).astype('float32')
    
    waveforms -= 32768
    
    return sample_numbers, waveforms, header

