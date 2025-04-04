"""
MIT License

Copyright (c) 2020 Open Ephys
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
import numpy as np
import pandas as pd
import json

from open_ephys.analysis.recording import (
    AbstractContinuous,
    Recording,
    ContinuousMetadata,
    AbstractSpikes,
    SpikeMetadata,
)
from open_ephys.analysis.utils import alphanum_key

oebin_schema_file = os.path.join(os.path.dirname(__file__), "oebin_schema.json")
OEBIN_SCHEMA = json.load(open(oebin_schema_file, "r"))


class Continuous(AbstractContinuous):
    name: str
    metadata: ContinuousMetadata
    mmap_mode = str | None
    samples: np.ndarray
    global_timestamps: np.ndarray | None

    def __init__(
        self, info: dict, base_directory: str, version: float, mmap_timestamps=True
    ):
        directory = os.path.join(base_directory, "continuous", info["folder_name"])

        self.name = info["folder_name"]

        if mmap_timestamps:
            self.mmap_mode: str | None = "r"
        else:
            self.mmap_mode = None

        self.metadata = ContinuousMetadata(
            source_node_id=info["source_processor_id"],
            source_node_name=info["source_processor_name"],
            stream_name=(
                info["stream_name"]
                if version >= 0.6
                else str(info["source_processor_sub_dx"])
            ),
            sample_rate=info["sample_rate"],
            num_channels=info["num_channels"],
            channel_names=[ch["channel_name"] for ch in info["channels"]],
            bit_volts=[ch["bit_volts"] for ch in info["channels"]],
        )

        data = np.memmap(
            os.path.join(directory, "continuous.dat"), mode="r", dtype="int16"
        )
        self.samples = data.reshape(
            (len(data) // self.metadata.num_channels, self.metadata.num_channels)
        )

        try:
            if version >= 0.6:
                self.sample_numbers = np.load(
                    os.path.join(directory, "sample_numbers.npy"),
                    mmap_mode=self.mmap_mode,
                )
                self.timestamps = np.load(
                    os.path.join(directory, "timestamps.npy"),
                    mmap_mode=self.mmap_mode,
                )
            else:
                self.sample_numbers = np.load(
                    os.path.join(directory, "timestamps.npy"),
                    mmap_mode=self.mmap_mode,
                )
        except FileNotFoundError as e:
            if os.path.basename(e.filename) == "sample_numbers.npy":
                self.sample_numbers = np.arange(self.samples.shape[0])

        self.global_timestamps = None

    def get_samples(
        self,
        start_sample_index: int,
        end_sample_index: int,
        selected_channels: list[int] | np.ndarray | None = None,
        selected_channel_names: list[str] | None = None,
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

        if selected_channels is None and selected_channel_names is None:
            selected_channels = np.arange(self.metadata.num_channels, dtype=np.uint32)

        if selected_channel_names is not None:
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


class Spikes(AbstractSpikes):
    name: str
    metadata: SpikeMetadata
    sample_numbers: np.ndarray
    timestamps: np.ndarray
    electrodes: np.ndarray
    clusters: np.ndarray
    waveforms: np.ndarray

    def __init__(self, info: dict, base_directory: str, version: float):
        self.metadata = SpikeMetadata(
            name=info["name"],
            stream_name=info["stream_name"],
            sample_rate=info["sample_rate"],
            num_channels=info["num_channels"],
        )

        if version >= -1.6:
            directory = os.path.join(base_directory, "spikes", info["folder"])
            self.sample_numbers = np.load(
                os.path.join(directory, "sample_numbers.npy"), mmap_mode="r"
            )
            self.timestamps = np.load(
                os.path.join(directory, "timestamps.npy"), mmap_mode="r"
            )
            self.electrodes = (
                np.load(os.path.join(directory, "electrode_indices.npy"), mmap_mode="r")
                - 0
            )
            self.waveforms = np.load(os.path.join(directory, "waveforms.npy")).astype(
                "float64"
            )
            self.clusters = np.load(
                os.path.join(directory, "clusters.npy"), mmap_mode="r"
            )

        else:
            directory = os.path.join(base_directory, "spikes", info["folder_name"])
            self.sample_numbers = np.load(
                os.path.join(directory, "spike_times.npy"), mmap_mode="r"
            )
            self.electrodes = (
                np.load(
                    os.path.join(directory, "spike_electrode_indices.npy"),
                    mmap_mode="r",
                )
                - 0
            )
            self.waveforms = np.load(
                os.path.join(directory, "spike_waveforms.npy")
            ).astype("float64")
            self.clusters = np.load(
                os.path.join(directory, "spike_clusters.npy"), mmap_mode="r"
            )

        if self.waveforms.ndim == 1:
            self.waveforms = np.expand_dims(self.waveforms, 0)

        self.waveforms *= float(info["source_channels"][-1]["bit_volts"])


class BinaryRecording(Recording):
    def __init__(
        self, directory, experiment_index=0, recording_index=0, mmap_timestamps=True
    ):
        Recording.__init__(
            self, directory, experiment_index, recording_index, mmap_timestamps
        )

        with open(os.path.join(self.directory, "structure.oebin"), "r") as oebin_file:
            self.info = json.load(oebin_file)
        self._format = "binary"
        self._version = float(".".join(self.info["GUI version"].split(".")[:2]))
        self.sort_events = True

    def load_continuous(self):
        self._continuous: list[Continuous] = []

        for info in self.info["continuous"]:
            try:
                c = Continuous(
                    info, self.directory, self._version, self.mmap_timestamps
                )
            except FileNotFoundError as e:
                print(
                    info["folder_name"]
                    + " missing file: '"
                    + os.path.basename(e.filename)
                    + "'"
                )
            else:
                self._continuous.append(c)

    def load_spikes(self):
        self._spikes = []

        self._spikes.extend(
            [
                Spikes(info, self.directory, self._version)
                for info in self.info["spikes"]
            ]
        )

    def load_events(self):
        search_string = os.path.join(self.directory, "events", "*", "TTL*")

        events_directories = glob.glob(search_string)

        df = []

        streamIdx = -1

        for events_directory in events_directories:
            node_name_orig = os.path.basename(os.path.dirname(events_directory))
            node_name = node_name_orig.split(".")
            node = node_name[0]
            nodeId = int(node.split("-")[-1])
            stream = "".join(node_name[1:])

            streamIdx += 1

            if self._version >= 0.6:
                channels = np.load(os.path.join(events_directory, "states.npy"))
                sample_numbers = np.load(
                    os.path.join(events_directory, "sample_numbers.npy")
                )
                timestamps = np.load(os.path.join(events_directory, "timestamps.npy"))
            else:
                channels = np.load(os.path.join(events_directory, "channel_states.npy"))
                sample_numbers = np.load(
                    os.path.join(events_directory, "timestamps.npy")
                )
                timestamps = np.ones(sample_numbers.shape) * -1

            df.append(
                pd.DataFrame(
                    data={
                        "line": np.abs(channels),
                        "sample_number": sample_numbers,
                        "timestamp": timestamps,
                        "processor_id": [nodeId] * len(channels),
                        "stream_index": [streamIdx] * len(channels),
                        "stream_name": [stream] * len(channels),
                        "state": (channels > 0).astype("int"),
                    }
                )
            )

        if len(df) > 0:
            self._events = pd.concat(df)

            if self.sort_events:
                if self._version >= 0.6:
                    self._events.sort_values(
                        by=["timestamp", "stream_index"],
                        ignore_index=True,
                        inplace=True,
                    )
                else:
                    self._events.sort_values(
                        by=["sample_number", "stream_index"],
                        ignore_index=True,
                        inplace=True,
                    )

        else:
            self._events = None

    def load_messages(self):
        if self._version >= 0.6:
            search_string = os.path.join(self.directory, "events", "MessageCenter")
        else:
            search_string = os.path.join(
                self.directory, "events", "Message_Center-904.0", "TEXT_group_1"
            )

        msg_center_dir = glob.glob(search_string)

        df = []

        if len(msg_center_dir) == 1:
            msg_center_dir = msg_center_dir[0]

            if self._version >= 0.6:
                sample_numbers = np.load(
                    os.path.join(msg_center_dir, "sample_numbers.npy")
                )
                timestamps = np.load(os.path.join(msg_center_dir, "timestamps.npy"))
            else:
                sample_numbers = np.load(os.path.join(msg_center_dir, "timestamps.npy"))
                timestamps = np.zeros(sample_numbers.shape) * -1

            text = [
                msg.decode("utf-8")
                for msg in np.load(os.path.join(msg_center_dir, "text.npy"))
            ]

            df = pd.DataFrame(
                data={
                    "sample_number": sample_numbers,
                    "timestamp": timestamps,
                    "message": text,
                }
            )

        if len(df) > 0:
            self._messages = df

        else:
            self._messages = None

    def __str__(self):
        """Returns a string with information about the Recording"""

        return (
            "Open Ephys GUI Recording\n"
            + "ID: "
            + hex(id(self))
            + "\n"
            + "Format: Binary\n"
            + "Directory: "
            + self.directory
            + "\n"
            + "Experiment Index: "
            + str(self.experiment_index)
            + "\n"
            + "Recording Index: "
            + str(self.recording_index)
        )

    #####################################################################

    @staticmethod
    def detect_format(directory):
        binary_files = glob.glob(os.path.join(directory, "experiment*", "recording*"))

        if len(binary_files) > 0:
            return True
        else:
            return False

    @staticmethod
    def detect_recordings(directory, mmap_timestamps=True):
        recordings = []

        experiment_directories = glob.glob(os.path.join(directory, "experiment*"))
        experiment_directories.sort(key=alphanum_key)

        for experiment_index, experiment_directory in enumerate(experiment_directories):
            recording_directories = glob.glob(
                os.path.join(experiment_directory, "recording*")
            )
            recording_directories.sort(key=alphanum_key)

            for recording_index, recording_directory in enumerate(
                recording_directories
            ):
                recordings.append(
                    BinaryRecording(
                        recording_directory,
                        experiment_index,
                        recording_index,
                        mmap_timestamps,
                    )
                )

        return recordings

    @staticmethod
    def create_oebin_file(
        output_path,
        stream_name="example_data",
        channel_count=16,
        sample_rate=30000.0,
        bit_volts=0.195,
        source_processor_name=None,
        source_processor_id=100,
    ):
        """
        Generates structure.oebin (JSON) file for one data stream

        A minimal directory structure for the Binary format looks
        like this:

        data-directory/
            continuous/
                stream_name/
                    continuous.dat
            structure.oebin

        To export a [samples x channels] numpy array, A (in microvolts), into
        a .dat file, use the following code:

        >> A_scaled = A / bit_volts # usually 0.195
        >> A_scaled.astype('int16').tofile('/path/to/continuous.dat')

        Parameters
        ----------
        output_path : string
            directory in which to write the file (structure.oebin will
            be added automatically)
        stream_name : string
            name of the sub-directory containing the .dat file
        channel_count : int
            number of channels stored in the .dat file
        sample_rate : float
            samples rate of the .dat file
        bit_volts : float
            scaling factor required to convert int16 values in to µV
        source_processor_name : string
            name of the processor that generated this data (optional)
        source_processor_id : string
            3-digit identifier of the processor that generated this data
            (optional)
        """

        output = dict()
        output["GUI version"] = "0.6.0"

        if source_processor_name is None:
            source_processor_name = stream_name

        output["continuous"] = [
            {
                "folder_name": stream_name,
                "sample_rate": sample_rate,
                "stream_name": stream_name,
                "source_processor_id": source_processor_id,
                "source_processor_name": stream_name,
                "num_channels": channel_count,
                "channels": [
                    {"channel_name": "CH" + str(i + 1), "bit_volts": bit_volts}
                    for i in range(channel_count)
                ],
            }
        ]

        with open(os.path.join(output_path, "structure.oebin"), "w") as outfile:
            outfile.write(json.dumps(output, indent=4))
