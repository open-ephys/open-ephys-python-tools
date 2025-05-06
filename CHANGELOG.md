# `open-ephys-python-tools` Changelog

## Unreleased

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