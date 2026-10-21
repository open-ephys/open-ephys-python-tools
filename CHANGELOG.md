# `open-ephys-python-tools` Changelog

## Unreleased

- Support the NWB files written by the AqNWB-based NWB Format plugin (NWB 2.11); files written by earlier
  versions of the plugin can still be read
  - Sample numbers are read from `sync/sample_numbers`, and the sample rate from `starting_time.rate` or the
    timestamps (instead of `timestamps.interval`, which NWB fixes to 1)
  - Continuous data and spikes are scaled with `data.conversion * channel_conversion`, as specified by NWB
    (files of earlier plugin versions store the factor in both, so only `channel_conversion` is applied for them)
  - TTL events are read from the `EventsTable`s in `/events`, which are named as the Binary event folders
    (`<processor>-<id>.<stream>.TTL`)
- `NwbRecording.load_messages` is implemented (new and previous NWB layout)
- Added a v1.1.0 NWB test file and tests

## 1.0.0

- Dropped support for Python < 3.9
- Refactoring without new functionality or API changes
  - The `Continuous` and `Spike` classes of the three formats now have an explicit interface
    (i.e. abstract parent class) and have been renamed to `BinaryContinuous`, `BinarySpike` etc.
  - The metadata of `Continuous` and `Spike` in the analysis package now are typed dataclasses
    instead of `dict` objects . This makes accessing metadata more reliable.
  - Type hints have been added to the `analysis` package.
  - Automated tests for reading Binary, NWB and OpenEphys data formats have been added.
  - Added a `RecordingFormat` enum for the three formats
  - Added a JSON schema for validating oebin files
  - Added a `uv.lock` file for reproducible development environments.
- `BinaryContinuous` and `BinarySpike` now have `__str__` methods to give an overview over
  their contents.

## 0.1.13
- Improve NWB format loading
- Add method for selecting channels by name

## 0.1.12
- Fix bug in global timestamp computation

## 0.1.11
- Ensure experiment and recording directories are sorted alphanumericaly

## 0.1.10
- Add option to load events without sorting by timestamp

## 0.1.9
- Allow continuous timestamps to be loaded without memory mapping (necessary when timestamp file will be overwritten)

## 0.1.8
- Change indexing method for extracting processor ID in NwbRecording

## 0.1.7
- Raise exception if no events exist on a selected line for global timestamp computation
- Add option to ignore a sample interval when computing global timestamps

## 0.1.6
- Add `config` method to `OpenEphysHTTPServer` class

## 0.1.5
- Speed up loading of Open Ephys data format
- Add stream names to NWB and Open Ephys events

## 0.1.4

- Include `source_processor_id` and `source_processor_name` when writing .oebin file
- If sample numbers are not available in a Binary format `continuous` folder, create default values

## 0.1.3

- Fix bug in loading sample numbers with Open Ephys format (last value was previously truncated)
- Load Binary format timestamps and sample numbers as memory-mapped arrays
- Update global timestamp synchronization to use latest naming conventions

## 0.1.2

- Fix bug in sending TTLs when using NetworkControl object
- Fix docstring for EventListener class
- Use absolute URLs in README, so the links work on PyPI site

## 0.1.1

- Add logo as link in README so it shows up on PyPI project description

## 0.1.0 (first release on PyPI)

### `analysis` module

- Reads data from Binary, NWB, and Open Ephys formats
- Binary format module is backwards compatible with version `0.5.x`, other modules only work with data saved by version `0.6.x` and higher.

### `control` module

- `OpenEphysHTTPServer` class communicates with the GUI's built-in HTTP server (available in version `0.6.x` and higher).
- `NetworkControl` class communicates with the [Network Events](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html) plugin, which is also available in version `0.5.x`.

### `streaming` module

- `EventListener` class receives spikes and events from the [Event Broadcaster](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html) plugin installed in GUI version `0.6.x` and higher.