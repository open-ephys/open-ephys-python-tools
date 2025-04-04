from calendar import c
from pyexpat.errors import messages
from numpy import isin
import pandas
import pytest
import os
import open_ephys.analysis as oe
from open_ephys.analysis.formats import BinaryRecording
from open_ephys.analysis.formats.BinaryRecording import Continuous, Spikes, OEBIN_SCHEMA
from open_ephys.analysis.recording import ContinuousMetadata, SpikeMetadata
import json
import jsonschema

PLUGIN_GUI_VERSION = "v0.6.7"


@pytest.fixture
def binary_file_path():
    return os.path.join(
        os.path.dirname(__file__), "data", f"{PLUGIN_GUI_VERSION}_Binary"
    )


@pytest.fixture
def binary_recording_correct_continuous_metadata():
    return ContinuousMetadata(
        source_node_id=100,
        source_node_name="File Reader",
        stream_name="example_data",
        sample_rate=40000.0,
        num_channels=16,
        channel_names=[f"CH{i}" for i in range(1, 17)],
        bit_volts=[0.05000000074505806] * 16,
    )


@pytest.fixture
def binary_recording_correct_spike_metadata():
    return SpikeMetadata(
        name="Stereotrode 1",
        stream_name="example_data",
        sample_rate=40000.0,
        num_channels=2,
    )


@pytest.fixture
def binary_session(binary_file_path: str):
    return oe.Session(binary_file_path)


@pytest.fixture
def recording_with_continuous_data(binary_session: oe.Session):
    # Assuming the first record node has continuous data for testing
    return binary_session.recordnodes[0].recordings[0]


@pytest.fixture
def binary_recording_with_spike_data(binary_session: oe.Session):
    # Assuming the second record node has spike data for testing
    return binary_session.recordnodes[1].recordings[0]


def test_validate_oebin(binary_file_path):
    oebin_file = os.path.join(
        binary_file_path,
        "Record Node 101",
        "experiment1",
        "recording1",
        "structure.oebin",
    )
    oebin_json = json.load(open(oebin_file, "r"))
    jsonschema.validate(instance=oebin_json, schema=OEBIN_SCHEMA)


def test_open_session(binary_file_path: str):
    session = oe.Session(binary_file_path)
    assert session.directory == binary_file_path
    assert session.recordnodes is not None
    assert len(session.recordnodes) > 0
    assert all(isinstance(node, oe.RecordNode) for node in session.recordnodes)
    assert all([node.format == "binary" for node in session.recordnodes])


def test_continuous_data(
    recording_with_continuous_data: BinaryRecording,
    binary_recording_correct_continuous_metadata: ContinuousMetadata,
):
    assert recording_with_continuous_data.continuous is not None

    assert len(recording_with_continuous_data.continuous) > 0

    cont: Continuous = recording_with_continuous_data.continuous[0]
    assert cont.name == "File_Reader-100.example_data/"
    assert cont.samples.shape == (131362, 16)
    assert cont.metadata == binary_recording_correct_continuous_metadata


def test_spike_data(
    binary_recording_with_spike_data: BinaryRecording,
    binary_recording_correct_spike_metadata: SpikeMetadata,
):
    assert binary_recording_with_spike_data.spikes is not None
    nChannels = 2
    nSamplesPerWaveForm = 40
    nSpikes = 189

    assert len(binary_recording_with_spike_data.spikes) > 0

    spike: Spikes = binary_recording_with_spike_data.spikes[0]
    assert spike.waveforms.shape == (nSpikes, nChannels, nSamplesPerWaveForm)
    assert spike.clusters.shape == (nSpikes,)
    assert spike.metadata == binary_recording_correct_spike_metadata


def test_messages(binary_recording_with_spike_data: BinaryRecording):
    assert binary_recording_with_spike_data.messages is not None
    messages = binary_recording_with_spike_data.messages
    assert len(messages) > 0
    assert isinstance(messages, pandas.DataFrame)
    expected_columns = ["sample_number", "timestamp", "message"]
    assert list(messages.columns) == expected_columns
    nMessages = 14
    assert len(messages) == nMessages


def test_events(binary_recording_with_spike_data: BinaryRecording):
    assert binary_recording_with_spike_data.events is not None
    events = binary_recording_with_spike_data.events
    assert len(events) > 0
    assert isinstance(events, pandas.DataFrame)

    expected_columns = [
        "line",
        "sample_number",
        "timestamp",
        "processor_id",
        "stream_index",
        "stream_name",
        "state",
    ]
    assert list(events.columns) == expected_columns
    assert len(events) == 128
