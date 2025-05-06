"""
MIT License

Copyright (c) 2020-2025 Open Ephys
Copyright (c) 2025 Joscha Schmiedt (joscha@schmiedt.dev)

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
from pathlib import Path
import h5py as h5
import numpy as np
import pandas as pd

from open_ephys.analysis.recording import (
    Continuous,
    ContinuousMetadata,
    Spikes,
    SpikeMetadata,
    RecordingFormat,
    Recording,
)


class NwbSpikes(Spikes):
    def __init__(self, nwb: h5.File, dataset: str):
        self.metadata = SpikeMetadata(
            name=dataset.split(".")[-1],
            stream_name=dataset.split(".")[-2],
            num_channels=nwb["acquisition"][dataset]["data"][()].shape[1],
            sample_rate=None,  # FIXME:
        )

        self.timestamps = nwb["acquisition"][dataset]["timestamps"][()]
        self.sample_numbers = nwb["acquisition"][dataset]["sync"][()]
        self.waveforms = nwb["acquisition"][dataset]["data"][()].astype("float64")

        self.waveforms *= nwb["acquisition"][dataset]["channel_conversion"][0] * 1e6


class NwbContinuous(Continuous):
    def __init__(self, nwb: h5.File, dataset: str):

        source_node = dataset.split(".")[0]
        stream_name = dataset.split(".")[1]
        source_node_id = int(source_node[-3:])
        source_node_name = source_node[:-4]

        self.metadata = ContinuousMetadata(
            source_node_id=source_node_id,
            source_node_name=source_node_name,
            stream_name=stream_name,
            sample_rate=np.around(
                1 / nwb["acquisition"][dataset]["timestamps"].attrs["interval"], 1
            ),
            num_channels=nwb["acquisition"][dataset]["data"].shape[1],
            bit_volts=list(nwb["acquisition"][dataset]["channel_conversion"][()] * 1e6),
            channel_names=None,  # TODO: add this
        )
        self.samples = nwb["acquisition"][dataset]["data"]
        self.sample_numbers = nwb["acquisition"][dataset]["sync"]
        self.timestamps = nwb["acquisition"][dataset]["timestamps"]

        self.global_timestamps = None

    def get_samples(
        self,
        start_sample_index,
        end_sample_index,
        selected_channels=None,
        selected_channel_names=None,
    ):
        """
        Returns samples scaled to microvolts. Converts sample values
        from 16-bit integers to 64-bit floats.

        Parameters
        ----------
        start_sample_index : int
            Index of the first sample to return
        end_sample_index : int
            Index of the last sample to return
        selected_channels : numpy.ndarray, optional
            Selects a subset of channels to return based on index.
            If no channels are selected, all channels are returned.
        selected_channel_names : List[str], optional
            Selects a subset of channels to return based on name.
            If no channels are selected, all channels are returned.

        Returns
        -------
        samples : numpy.ndarray (float64)

        """

        if selected_channels is not None and selected_channel_names is not None:
            raise ValueError(
                "Cannot specify both `selected_channels`"
                + " and `selected_channel_names` as input arguments"
            )

        if selected_channel_names:
            selected_channels = [
                self.metadata.channel_names.index(value)
                for value in selected_channel_names
            ]
            selected_channels = np.array(selected_channels, dtype=np.uint32)

        samples = self.samples[
            start_sample_index:end_sample_index, selected_channels
        ].astype("float64")

        for idx, ch in enumerate(selected_channels):
            samples[:, idx] = samples[:, idx] * self.metadata.bit_volts[ch]

        return samples


class NwbRecording(Recording):

    def __init__(self, directory: str, experiment_index=0, recording_index=0):

        Recording.__init__(self, directory, experiment_index, recording_index)
        self._format = RecordingFormat.nwb
        self.nwb = h5.File(
            os.path.join(
                self.directory, "experiment" + str(self.experiment_index + 1) + ".nwb"
            ),
            "r",
        )

    def __delete__(self):

        self.nwb.close()

    def load_continuous(self):

        datasets = list(self.nwb["acquisition"].keys())

        self._continuous = [
            NwbContinuous(self.nwb, dataset)
            for dataset in datasets
            if self.nwb["acquisition"][dataset].attrs["neurodata_type"]
            == "ElectricalSeries"
        ]

    def load_spikes(self):

        datasets = list(self.nwb["acquisition"].keys())

        self._spikes = [
            NwbSpikes(self.nwb, dataset)
            for dataset in datasets
            if self.nwb["acquisition"][dataset].attrs["neurodata_type"]
            == "SpikeEventSeries"
        ]

    def load_events(self):

        datasets = list(self.nwb["acquisition"].keys())

        events = []
        processor_ids = []

        for dataset in datasets:

            if dataset[-4:] == ".TTL":

                processor_id = int(dataset.split(".")[0].split("-")[-1])
                stream_name = dataset.split(".")[1]

                if processor_id not in processor_ids:
                    processor_ids.append(processor_id)
                    stream_id = 0
                else:
                    stream_id += 1

                ds = self.nwb["acquisition"][dataset]
                channel_states = ds["data"]
                sample_numbers = ds["sync"]
                timestamps = ds["timestamps"]

                events.append(
                    pd.DataFrame(
                        data={
                            "line": np.abs(channel_states),
                            "timestamp": timestamps,
                            "sample_number": sample_numbers,
                            "processor_id": [processor_id] * len(channel_states),
                            "stream_index": [stream_id] * len(channel_states),
                            "stream_name": [stream_name] * len(channel_states),
                            "state": (np.sign(channel_states) + 1 / 2).astype("int"),
                        }
                    )
                )
        self._events = pd.concat(events).sort_values(
            by=["sample_number", "stream_index"], ignore_index=True
        )

    def load_messages(self):
        raise NotImplementedError(
            "Loading messages from NWB2 format is noy yet implemented."
        )

    def __str__(self):
        """Returns a string with information about the Recording"""

        return (
            "Open Ephys GUI Recording\n"
            + "ID: "
            + hex(id(self))
            + "\n"
            + "Format: NWB 2.0\n"
            + "Directory: "
            + self.directory
            + "\n"
            + "Experiment Index: "
            + str(self.experiment_index)
            + "\n"
            + "Recording Index: "
            + str(self.recording_index)
        )

    ###############################################################

    @staticmethod
    def detect_format(directory):
        nwb_files = glob.glob(os.path.join(directory, "*.nwb"))

        if len(nwb_files) > 0:
            return True
        else:
            return False

    @staticmethod
    def detect_recordings(directory, mmap_timestamps=True):

        recordings = []

        nwb_files = glob.glob(os.path.join(directory, "experiment*.nwb"))
        nwb_files.sort()

        for experiment_index, file in enumerate(nwb_files):

            try:
                f = h5.File(file, "r")
            except BlockingIOError:
                print(
                    "Error: "
                    + file
                    + "\nis likely still in use. Try closing the GUI and re-loading the session object."
                )
            else:
                recordings.append(NwbRecording(directory, experiment_index, 0))
                f.close()

        return recordings
