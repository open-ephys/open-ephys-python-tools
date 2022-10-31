# `open_ephys.control`

This module makes it possible to control the [Open Ephys GUI](https://open-ephys.org/gui) via a Python process, either running locally or over a network.

## Usage

### Initialization

First, load the module:

```python
from open_ephys.control import OpenEphysHTTPServer
```

To control a GUI instance running on the same machine, simply enter:

```python
gui = OpenEphysHTTPServer()
```

To specify a custom IP address, use:

```python
gui = OpenEphysHTTPServer('10.128.50.93')
```

Note that the port number (`37497`) will be added automatically.

### Starting and stopping acquisition

To start acquisition, enter:

```python
gui.acquire()
```

To stop acquisition, enter:

```python
gui.idle()
```
    
To query acquisition status, use:

```python
gui.status()
```

### Starting and stopping recording

To start recording, enter:

```python
gui.record()
```

To stop recording while keeping acquisition active, enter:

```python
gui.acquire()
```

### Sending TTL events

It's possible to remotely generate TTL events on one of the GUI's data stream by adding a [NetworkEvents](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html) plugin to the signal chain.

This functionality is independent of the Open Ephys HTTP Server, and therefore requires a separate class.

To send TTL events to an instance running on the same machine, simply enter:

```python
network_control = NetworkControl()
```

To specify a custom IP address or port number, use:

```python
network_control = NetworkControl(ip_address = '10.127.50.1',
                     port = 2000)
```

To send a TTL "ON" event, enter:

```python
network_control.send_ttl(line = 5, state = 1)
```

To send a TTL "OFF" event, enter:

```python
network_control.send_ttl(line = 5, state = 0)
```

The `NetworkControl` class can also be used to interact with v0.5.x of the GUI, which does not have a built-in HTTP Server.