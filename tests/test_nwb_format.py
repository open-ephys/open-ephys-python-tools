import os
import pandas
import pytest
from open_ephys.analysis import Session, RecordNode
from open_ephys.analysis.formats.NwbRecording import (
    NwbRecording,
    NwbSpikes,
    NwbContinuous,
)
from open_ephys.analysis.recording import ContinuousMetadata, SpikeMetadata

PLUGIN_GUI_VERSION = "v0.6.7"


@pytest.fixture
def nwb_file_path():
    return os.path.join(os.path.dirname(__file__), "data", f"{PLUGIN_GUI_VERSION}_NWB")


@pytest.fixture
def nwb_recording_correct_continuous_metadata():
    return ContinuousMetadata(
        source_node_id=100,
        source_node_name="File Reader",
        stream_name="example_data",
        sample_rate=40000.0,
        num_channels=16,
        channel_names=None,  # NwbFormat does not yet have channel name reconstruction
        bit_volts=[0.05] * 16,
    )


@pytest.fixture
def nwb_recording_correct_spike_metadata():
    return SpikeMetadata(
        name="Stereotrode 1",
        stream_name="example_data",
        sample_rate=None,
        num_channels=2,
    )


@pytest.fixture
def nwb_session(nwb_file_path: str):
    return Session(nwb_file_path)


@pytest.fixture
def recording_with_continuous_data(nwb_session: Session) -> NwbRecording:
    # Assuming the first recording has continuous data for testing
    return nwb_session.recordnodes[0].recordings[0]


@pytest.fixture
def nwb_recording_with_spike_data(nwb_session):
    return nwb_session.recordnodes[0].recordings[0]


def test_open_session(nwb_session: Session, nwb_file_path):
    session = nwb_session
    assert session.directory == nwb_file_path
    assert session.recordnodes is not None
    assert len(session.recordnodes) > 0
    assert all(isinstance(node, RecordNode) for node in session.recordnodes)
    assert all([node.format == "nwb" for node in session.recordnodes])


def test_continuous_data(
    recording_with_continuous_data: NwbRecording,
    nwb_recording_correct_continuous_metadata: ContinuousMetadata,
):
    assert recording_with_continuous_data.continuous is not None
    assert len(recording_with_continuous_data.continuous) > 0

    assert isinstance(recording_with_continuous_data.continuous[0], NwbContinuous)
    cont = recording_with_continuous_data.continuous[0]
    assert cont.metadata == nwb_recording_correct_continuous_metadata


def test_spike_data(
    nwb_recording_with_spike_data: NwbRecording,
    nwb_recording_correct_spike_metadata: SpikeMetadata,
):
    assert nwb_recording_with_spike_data.spikes is not None
    nChannels = 2
    nSamplesPerWaveForm = 40
    nSpikes = 189

    assert len(nwb_recording_with_spike_data.spikes) > 0

    spike: NwbSpikes = nwb_recording_with_spike_data.spikes[0]
    assert spike.waveforms is not None
    assert spike.waveforms.shape == (nSpikes, nChannels, nSamplesPerWaveForm)
    assert spike.metadata == nwb_recording_correct_spike_metadata


def test_events(nwb_recording_with_spike_data: NwbRecording):
    nwb_recording_with_spike_data.load_events()
    assert nwb_recording_with_spike_data._events is not None
    events = nwb_recording_with_spike_data._events
    assert len(events) > 0
    assert isinstance(events, pandas.DataFrame)

    expected_columns = [
        "line",
        "timestamp",
        "sample_number",
        "processor_id",
        "stream_index",
        "stream_name",
        "state",
    ]
    assert list(events.columns) == expected_columns


def test_messages(nwb_recording_with_spike_data: NwbRecording):

    with pytest.raises(NotImplementedError):
        assert nwb_recording_with_spike_data.messages is not None

    # messages = nwb_recording_with_spike_data.messages
    # assert len(messages) > 0
    # assert isinstance(messages, pandas.DataFrame)
    # expected_columns = ["sample_number", "timestamp", "message"]
    # assert list(messages.columns) == expected_columns
    # nMessages = 14
    # assert len(messages) == nMessages
