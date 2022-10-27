# `open_ephys.analysis`

This module is intended for loading data saved by the [Open Ephys GUI](https://open-ephys.org/gui). It makes data accessible through a common interface, regardless of which format it's stored in.

To get started, simply run:

```python

from open_ephys.analysis import Session

directory = '/path/to/data/2020-11-10_09-28-30' # for example

session = Session(directory)
```

This will create a `Session` object that holds information about your recording session. This includes all of the data that was saved in the specified directory, although the data won't be loaded into memory until it's requested.

## How recordings are organized

The Open Ephys GUI provides a great deal of flexibility when it comes to saving data. Data is saved by any Record Nodes that have been inserted into the signal chain. This makes is possible to record both the raw data as well as data that has been transformed by different processing stages. By default, all Record Nodes will save data to the same directory, in sub-folders named "Record Node <ID>," where <ID> is the Record Node's processor ID. Each Record Node can store data in a different format, although the [Binary format](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Binary-format.html) is the default format that is recommended for most use cases.

To access the data for the first Record Node, enter:

```python
recordnode = session.recordnodes[0]
```

If data from multiple Record Nodes is stored in the same directory, you can use the `print` function to view information about the Record Nodes in the `Session` object, e.g.:

```
>> print(session)

Open Ephys Recording Session Object
Directory: /path/to/session/2021-01-10_11-53-13

<object>.recordnodes:
  Index 0: Record Node 103 (binary format)
  Index 1: Record Node 105 (open-ephys format)

```

Within each Record Node, recordings are grouped by "experiments" and "recordings." A new "experiment" begins whenever data acquisition is stopped and re-started, as this re-sets the incoming hardware sample numbers to zero. Within a given experiment, all of the sample numbers are relative to a common start time. Starting and stopped recording (but not acquisition) in the GUI will initiate a new "recording." Each recording will have contiguous sample numbers that increment by 1 for each sample.

The `open_ephys.analysis` module loads does not have a separate hierarchical level for experiments. Instead, each recording (regardless of the experiment index) is accessed through the `session.recordnodes[N].recordings` list.

To view information about a specific recording

Note that Open Ephys starts numbering experiments and recordings at 1, but the `Recording` object stores the zero-based indices:

```
>> print(session.recordnodes[0].recording[0])

Open Ephys GUI Recording
ID: 0x7fe5c80babb0
Format: Binary
Directory: /path/to/session/2021-01-10_11-53-13/Record Node 103
Experiment Index: 0
Recording Index: 0

```

## Loading continuous data

Continuous data for each recording is accessed via the `.continuous` property of each `Recording` object. This returns a list of continuous data, grouped by processor/sub-processor. For example, if you have two data streams merged into a single Record Node, each data stream will be associated with a different processor ID. If you're recording Neuropixels data, each probe's data stream will be stored in a separate sub-processor, which must be loaded individually.

Each `continuous` object has four properties:

- `samples` - a `numpy.ndarray` that holds the actual continuous data with dimensions of samples x channels. For Binary, NWB, and Kwik format, this will be a memory-mapped array (i.e., the data will only be loaded into memory when specific samples are accessed)
- `sample_numbers` - a `numpy.ndarray` that holds the sample indices. This will have the same size as the first dimension of the `samples` array
- `timestamps` - a `numpy.ndarray` that holds global timestamps (in seconds) for each sample, assuming all data streams were synchronized in this recording. This will have the same size as the first dimension of the `samples` array
- `metadata` - a `dict` containing information about this data, such as the ID of the processor it originated from.

### Using the Open Ephys data format

Because the data files from the Open Ephys format cannot be memory-mapped effectively, all of the samples must be loaded into memory. For long recordings, it may not be possible to load all of the channels at once. Before requesting the `samples` property of a `continuous` object in Open Ephys format, you can uses the following functions to restrict the data to a certain sample range or a certain set of channels:

```python
>> recording = session.recordnodes[0].recording[0] # loads the sample numbers, timestamps, and metadata
>> recording.set_sample_range([10000, 50000])
>> recording.set_selected_channels([np.arange(10,15)])
>> recording.samples.shape  # loads the samples

(40000, 5)

```

## Loading event data

Event data for each recording is accessed via the `.events` property of each `Recording` object. This returns a pandas DataFrame with the following columns:

- `sample_number` - the sample index at which this event occurred
- `timestamps` - the global timestamp (in seconds) at which this event occurred (defaults to -1 if all streams were not synchronized)
- `channel` - the channel on which this event occurred
- `processor_id` - the ID of the processor from which this event originated
- `stream_index` - the index of the stream from which this event originated
- `state` - 1 or 0, to indicate whether this is a rising edge or falling edge event

## Loading spike data

If spike data has been saved by your Record Node (i.e., there is a Spike Detector or Spike Sorter upstream in the signal chain), this can be accessed via the `.spikes` property of each `Recording` object. This returns a list of spike sources, each of which has the following properties:

- `waveforms` - `numpy.ndarray` containing spike waveforms, with dimensions of spikes x channels x samples
- `sample_numbers` - `numpy.ndarray` of sample indices (one per spikes)
- `timestamps` - `numpy.ndarray` of global timestamps (in seconds)
- `electrodes` - `numpy.ndarray` containing the index of the electrode from which each spike originated
- `metadata` - `dict` with metadata about each electrode

## Synchronizing timestamps

If your recording contains data from multiple streams that were not synchronized during the recording, you'll likely want to synchronize their timestamps prior to further analysis.

Assuming they each have one event channel that was connected to the same _physical digital input line_, synchronization is straightforward.

First, indicate which event lines share the sync input (this will depend on your recording configuration):

```python
recording = session.recordnodes[0].recording[0]

recording.add_sync_line(8,          # TTL line number
                        102,        # processor ID
                        0,          # stream index (defaults to 0)
                        main=True)  # use as the main stream

recording.add_sync_line(1,          # TTL line number
                        100,        # processor ID
                        0,          # stream index (defaults to 0)
                        main=False) # align to the main stream

recording.add_sync_line(1,          # TTL line number
                        100,        # processor ID
                        1,          # stream index (defaults to 0)
                        main=False) # align to the main stream
```

You must have one and only one "main" stream, and at least one "auxiliary" stream for synchronization to work.

Next, running:

```python
recording.compute_global_timestamps()
```

will generate `global_timestamps` values for each `Continuous` object with a sync line, as well as a `global_timestamp` column in the `recording.events` DataFrame.

Now, you can work with your data aligned to a common timebase.
