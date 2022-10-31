# `open-ephys-python-tools` Changelog

## 0.1.0 (first release on PyPI)

### `analysis` module

- Reads data from Binary, NWB, and Open Ephys formats
- Binary format module is backwards compatible with version `0.5.x`, other modules only work with data saved by version `0.6.x` and higher.

### `control` module

- `OpenEphysHTTPServer` class communicates with the GUI's built-in HTTP server (available in version `0.6.x` and higher).
- `NetworkControl` class communicates with the [Network Events](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html) plugin, which is also available in version `0.5.x`.

### `streaming` module

- `EventListener` class receives spikes and events from the [Event Broadcaster](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html) plugin installed in GUI version `0.6.x` and higher.