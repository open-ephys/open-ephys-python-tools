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
    create_continuous_dict
)


def _is_legacy(group: h5.Group) -> bool:
    """Files written by the NWB plugin before v2 (AqNWB) store the sample numbers in a ``sync`` dataset"""
    return isinstance(group.get("sync"), h5.Dataset)


def _sample_numbers(group: h5.Group):
    """Sample numbers of a TimeSeries: ``sync/sample_numbers`` (NWB plugin >= 2) or the legacy ``sync`` dataset"""
    sync = group.get("sync")
    if isinstance(sync, h5.Dataset):
        return sync
    if isinstance(sync, h5.Group) and "sample_numbers" in sync:
        return sync["sample_numbers"]
    return None


def _conversion_to_microvolts(group: h5.Group) -> np.ndarray:
    """Per-channel factors to convert the stored values of an ElectricalSeries/SpikeEventSeries to microvolts.

    Files written by the NWB plugin before v2 store the factor both in ``data.conversion`` and in
    ``channel_conversion`` (i.e., applying both would scale twice), so only ``channel_conversion`` is used.
    Otherwise, values in volts are ``data * data.conversion * channel_conversion`` (NWB specification).
    """
    channel_conversion = group["channel_conversion"][()] if "channel_conversion" in group else np.array([1.0])
    conversion = 1.0 if _is_legacy(group) else float(group["data"].attrs.get("conversion", 1.0))
    return channel_conversion * conversion * 1e6


def _sample_rate(group: h5.Group) -> float:
    """Sample rate from ``starting_time.rate``, or estimated from the timestamps"""
    if "starting_time" in group:
        return float(group["starting_time"].attrs["rate"])
    timestamps = group["timestamps"][:1001]
    if len(timestamps) > 1:
        return float(np.around(1 / np.median(np.diff(timestamps)), 1))
    # very short legacy series: earlier versions of the plugin stored 1/sample_rate in timestamps.interval
    return float(np.around(1 / group["timestamps"].attrs["interval"], 1))


class NwbSpikes(Spikes):
    def __init__(self, nwb: h5.File, dataset: str):
        self.metadata = SpikeMetadata(
            name=dataset.split(".")[-1],
            stream_name=dataset.split(".")[-2],
            num_channels=nwb["acquisition"][dataset]["data"][()].shape[1],
            sample_rate=None,  # FIXME:
        )

        group = nwb["acquisition"][dataset]
        self.timestamps = group["timestamps"][()]
        sample_numbers = _sample_numbers(group)
        self.sample_numbers = sample_numbers[()] if sample_numbers is not None else None
        self.waveforms = group["data"][()].astype("float64")

        # all channels of a spike waveform use the same factor
        self.waveforms *= _conversion_to_microvolts(group)[0]


class NwbContinuous(Continuous):
    def __init__(self, nwb: h5.File, dataset: str):

        source_node = dataset.split(".")[0]
        stream_name = dataset.split(".")[1]
        source_node_id = int(source_node[-3:])
        source_node_name = source_node[:-4]

        group = nwb["acquisition"][dataset]
        num_channels = group["data"].shape[1]
        bit_volts = _conversion_to_microvolts(group)
        if len(bit_volts) == 1:
            bit_volts = np.repeat(bit_volts, num_channels)

        self.metadata = ContinuousMetadata(
            source_node_id=source_node_id,
            source_node_name=source_node_name,
            stream_name=stream_name,
            sample_rate=_sample_rate(group),
            num_channels=num_channels,
            bit_volts=list(bit_volts),
            channel_names=None,  # TODO: add this
        )
        self.samples = group["data"]
        self.sample_numbers = _sample_numbers(group)
        self.timestamps = group["timestamps"]

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

        names = [dataset.split(".")[1] for dataset in datasets
                 if self.nwb["acquisition"][dataset].attrs["neurodata_type"]
                 == "ElectricalSeries"]
        
        source_processor_ids = [
            dataset.split(".")[0].split('-')[1] for dataset in datasets
            if self.nwb["acquisition"][dataset].attrs["neurodata_type"]
            == "ElectricalSeries"]

        values = [
            NwbContinuous(self.nwb, dataset)
            for dataset in datasets
            if self.nwb["acquisition"][dataset].attrs["neurodata_type"]
            == "ElectricalSeries"
        ]

        for idx1, name1 in enumerate(names):
            for idx2, name2 in enumerate(names):
                if idx1 != idx2 and name1 == name2:
                    names[idx1] = name1 + "_" + source_processor_ids[idx1]
                    names[idx2] = name2 + "_" + source_processor_ids[idx2]
                    break

        self._continuous = create_continuous_dict(names, values)

    def load_spikes(self):

        datasets = list(self.nwb["acquisition"].keys())

        self._spikes = [
            NwbSpikes(self.nwb, dataset)
            for dataset in datasets
            if self.nwb["acquisition"][dataset].attrs["neurodata_type"]
            == "SpikeEventSeries"
        ]

    def load_events(self):

        events = []
        stream_indexes = {}

        def add_events(processor_id, stream_name, lines, states, timestamps, sample_numbers):
            if len(lines) == 0:
                return  # empty frames would turn the integer columns into floats in pd.concat
            # stream_index counts the event streams of each processor
            key = (processor_id, stream_name)
            if key not in stream_indexes:
                stream_indexes[key] = sum(1 for p, _ in stream_indexes if p == processor_id)
            events.append(
                pd.DataFrame(
                    data={
                        "line": lines,
                        "timestamp": timestamps,
                        "sample_number": sample_numbers,
                        # float, as in the Binary format and earlier versions of this reader
                        "processor_id": np.full(len(lines), processor_id, dtype="float64"),
                        "stream_index": np.full(len(lines), stream_indexes[key], dtype="float64"),
                        "stream_name": [stream_name] * len(lines),
                        "state": states,
                    }
                )
            )

        # NWB plugin >= 2: one EventsTable per TTL event channel in /events, named as the event folders of the
        # Binary format: "<processor>-<id>.<stream>.TTL" (further channels of the processor: "TTL_1", ...)
        for name, table in (self.nwb["events"].items() if "events" in self.nwb else []):
            if not {"line", "state", "sample_number", "timestamp"} <= set(table.keys()):
                continue
            parts = name.split(".")
            if len(parts) < 3 or not (parts[-1] == "TTL" or parts[-1].startswith("TTL_")):
                continue
            processor_id = int(parts[0].rsplit("-", 1)[-1])
            add_events(
                processor_id,
                ".".join(parts[1:-1]),
                table["line"][()].astype("int16") + 1,  # 1-based int16, as in the Binary format
                table["state"][()].astype("int"),
                table["timestamp"][()],
                table["sample_number"][()],
            )

        # NWB plugin < 2: TTL events as "<source>-<id>.<stream>.TTL" TimeSeries with data = +/-(line + 1)
        for dataset in self.nwb["acquisition"].keys():
            if dataset[-4:] == ".TTL":
                ds = self.nwb["acquisition"][dataset]
                channel_states = ds["data"][()]
                add_events(
                    int(dataset.split(".")[0].split("-")[-1]),
                    dataset.split(".")[1],
                    np.abs(channel_states),
                    (channel_states > 0).astype("int"),
                    ds["timestamps"][()],
                    ds["sync"][()],
                )

        if len(events) > 0:
            self._events = pd.concat(events).sort_values(
                by=["sample_number", "stream_index"], ignore_index=True
            )
        else:
            self._events = None

    def load_messages(self):

        # NWB plugin >= 2: EventsTable /events/messages; NWB plugin < 2: AnnotationSeries /acquisition/messages
        if "events" in self.nwb and "messages" in self.nwb["events"]:
            table = self.nwb["events"]["messages"]
            sample_numbers = table["sample_number"][()]
            timestamps = table["timestamp"][()]
            text = table["annotation"][()]
        elif "messages" in self.nwb["acquisition"] and isinstance(self.nwb["acquisition"]["messages"].get("sync"), h5.Dataset):
            series = self.nwb["acquisition"]["messages"]
            sample_numbers = series["sync"][()]
            timestamps = series["timestamps"][()]
            text = series["data"][()]
        else:
            self._messages = None
            return

        self._messages = pd.DataFrame(
            data={
                "sample_number": sample_numbers,
                "timestamp": timestamps,
                "message": [t.decode("utf-8") if isinstance(t, bytes) else str(t) for t in text],
            }
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
