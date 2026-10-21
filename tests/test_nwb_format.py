import os
import numpy as np
import pandas
import pytest
from open_ephys.analysis import Session, RecordNode
from open_ephys.analysis.formats.NwbRecording import (
    NwbRecording,
    NwbSpikes,
    NwbContinuous,
)
from open_ephys.analysis.recording import (
    ContinuousMetadata,
    RecordingFormat,
    SpikeMetadata,
)

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
    assert all([node.format == RecordingFormat.nwb for node in session.recordnodes])


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

    messages = nwb_recording_with_spike_data.messages
    assert isinstance(messages, pandas.DataFrame)
    assert len(messages) == 14
    assert list(messages.columns) == ["sample_number", "timestamp", "message"]
    assert all(isinstance(m, str) and len(m) > 0 for m in messages["message"])


# Files written by the AqNWB-based NWB plugin (GUI v1.1.0): File Reader -> Phase Detector -> Spike Detector ->
# Record Node (recording channels 1-4 of 16), two short recordings appended to the same file, two Message Center
# messages per recording
@pytest.fixture
def nwb_aqnwb_recording() -> NwbRecording:
    path = os.path.join(os.path.dirname(__file__), "data", "v1.1.0_NWB")
    return Session(path).recordnodes[0].recordings[0]


def test_aqnwb_continuous_data(nwb_aqnwb_recording: NwbRecording):
    cont = nwb_aqnwb_recording.continuous[0]
    assert isinstance(cont, NwbContinuous)
    assert cont.metadata.source_node_id == 100
    assert cont.metadata.source_node_name == "File Reader"
    assert cont.metadata.stream_name == "example_data"
    assert cont.metadata.sample_rate == 40000.0
    assert cont.metadata.num_channels == 4
    assert cont.metadata.bit_volts == pytest.approx([0.05] * 4)
    assert cont.samples.shape == (52012, 4)
    # sample numbers are stored in sync/sample_numbers
    assert len(cont.sample_numbers) == cont.samples.shape[0]
    assert len(cont.timestamps) == cont.samples.shape[0]
    samples = cont.get_samples(0, 10, selected_channels=np.arange(4))
    assert samples == pytest.approx(cont.samples[0:10, :] * 0.05)


def test_aqnwb_spike_data(nwb_aqnwb_recording: NwbRecording):
    spikes = nwb_aqnwb_recording.spikes
    assert [s.metadata.name for s in spikes] == ["Tetrode 1", "Tetrode 2"]
    assert [s.waveforms.shape for s in spikes] == [(533, 4, 40), (508, 4, 40)]
    for s in spikes:
        assert s.metadata.stream_name == "example_data"
        assert len(s.sample_numbers) == len(s.timestamps) == s.waveforms.shape[0]
        # waveforms in microvolts (data.conversion = bitVolts / 1e6), i.e., plausible spike amplitudes
        assert 10 < np.abs(s.waveforms).max() < 1000


def test_aqnwb_events(nwb_aqnwb_recording: NwbRecording):
    nwb_aqnwb_recording.load_events()
    events = nwb_aqnwb_recording._events
    assert list(events.columns) == [
        "line",
        "timestamp",
        "sample_number",
        "processor_id",
        "stream_index",
        "stream_name",
        "state",
    ]
    # Phase Detector (processor 104) output on line 1 of the example_data stream. It turns the line on at each
    # detected peak and only off after 2000 samples without a new peak, so (almost) all events have state 1
    assert set(events.processor_id) == {104}
    assert set(events.stream_name) == {"example_data"}
    assert set(events.line) == {1}
    assert set(events.state) <= {0, 1}
    assert (events.state == 1).any()
    assert len(events) == 576


def test_aqnwb_messages(nwb_aqnwb_recording: NwbRecording):
    messages = nwb_aqnwb_recording.messages
    assert list(messages.columns) == ["sample_number", "timestamp", "message"]
    assert list(messages.message) == [
        "first message of recording 1",
        "second message of recording 1",
        "first message of recording 2",
        "second message of recording 2",
    ]
