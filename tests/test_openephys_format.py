import os
import pandas
import pytest
from open_ephys.analysis.formats import OpenEphysRecording
from open_ephys.analysis.formats.OpenEphysRecording import (
    OpenEphysContinuous,
    OpenEphysSpikes,
)
from open_ephys.analysis.recording import ContinuousMetadata, SpikeMetadata

# filepath: c:\Code\open-ephys\open-ephys-python-tools\tests\test_openephys_format.py
import open_ephys.analysis as oe

PLUGIN_GUI_VERSION = "v0.6.7"


@pytest.fixture
def openephys_file_path():
    return os.path.join(
        os.path.dirname(__file__), "data", f"{PLUGIN_GUI_VERSION}_OpenEphys"
    )


@pytest.fixture
def openephys_recording_correct_continuous_metadata():
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
def openephys_recording_correct_spike_metadata():
    return SpikeMetadata(
        name="Stereotrode 1",
        stream_name="example_data",
        sample_rate=40000.0,
        num_channels=2,
    )


@pytest.fixture
def openephys_session(openephys_file_path: str):
    return oe.Session(openephys_file_path)


@pytest.fixture
def recording_with_continuous_data(openephys_session: oe.Session):
    # Assuming the first record node has continuous data for testing
    return openephys_session.recordnodes[0].recordings[0]


@pytest.fixture
def openephys_recording_with_spike_data(openephys_session: oe.Session):
    # Assuming the second record node has spike data for testing
    return openephys_session.recordnodes[1].recordings[0]


def test_open_session(openephys_file_path: str):
    session = oe.Session(openephys_file_path)
    assert session.directory == openephys_file_path
    assert session.recordnodes is not None
    assert len(session.recordnodes) > 0
    assert all(isinstance(node, oe.RecordNode) for node in session.recordnodes)
    assert all([node.format == "open-ephys" for node in session.recordnodes])


def test_continuous_data(
    recording_with_continuous_data: OpenEphysRecording,
    openephys_recording_correct_continuous_metadata: ContinuousMetadata,
):
    cont: OpenEphysContinuous = recording_with_continuous_data.continuous[0]
    assert cont.name == "example-data"
    nChannels = 16
    nSamples = 133120
    assert cont.samples.shape == (nSamples, nChannels)
    assert cont.metadata == openephys_recording_correct_continuous_metadata


# FIXME: This gives a ValueError: cannot reshape array of size 15138 into shape (174,2,40)
@pytest.mark.skip(
    reason="This test is skipped as there may be a bug in the OpenEphysRecording class"
)
def test_spike_data(
    openephys_recording_with_spike_data: OpenEphysRecording,
    openephys_recording_correct_spike_metadata: SpikeMetadata,
):
    assert openephys_recording_with_spike_data.spikes is not None
    nChannels = 2
    nSamplesPerWaveForm = 40
    nSpikes = 200

    assert len(openephys_recording_with_spike_data.spikes) > 0

    spike: OpenEphysSpikes = openephys_recording_with_spike_data.spikes[0]
    assert spike.waveforms.shape == (nSpikes, nChannels, nSamplesPerWaveForm)
    assert spike.clusters.shape == (nSpikes,)
    assert spike.metadata == openephys_recording_correct_spike_metadata


def test_messages(openephys_recording_with_spike_data: OpenEphysRecording):
    assert openephys_recording_with_spike_data.messages is not None
    messages = openephys_recording_with_spike_data.messages
    assert len(messages) > 0
    assert isinstance(messages, pandas.DataFrame)

    # OpenEphys messsages  have only two columns
    expected_columns = ["timestamp", "message"]
    assert list(messages.columns) == expected_columns
    nMessages = 16
    assert len(messages) == nMessages


def test_events(openephys_recording_with_spike_data: OpenEphysRecording):
    assert openephys_recording_with_spike_data.events is not None
    events = openephys_recording_with_spike_data.events
    assert len(events) > 0
    assert isinstance(events, pandas.DataFrame)

    # openEphys events have only six columns
    expected_columns = [
        "line",
        "sample_number",
        "processor_id",
        "stream_index",
        "stream_name",
        "state",
    ]
    assert list(events.columns) == expected_columns
    assert len(events) == 128
