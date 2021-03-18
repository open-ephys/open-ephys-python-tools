# `open_ephys.control`

This module makes it possible to control the [Open Ephys GUI](https://open-ephys.org/gui) via a Python process, either running locally or over a network.

Your GUI's signal chain must include a [NetworkEvents](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html) plugin in order for this module to work.

## Usage

### Initialization

To control a GUI instance running on the same machine, simply enter:

```python
gui = NetworkControl()
```

To specify a custom IP address or port number, use:

```python
gui = NetworkControl(ip_address = '10.127.50.1',
                     port = 2000)
```

### Starting and stopping acquisition

To start acquisition, enter:

```python
gui.start
```

To stop acquisition, enter:

```python
gui.stop
```
    
To query acquisition status, use:

```python
gui.is_acquiring
```

### Starting and stopping recording

To start recording, enter:

```python
gui.record
```

To stop recording while keeping acquisition active, enter:

```python
gui.stop_recording
```
    
To query recording status, use:

```python
gui.is_recording
```

### Sending TTL events

To send a TTL "ON" event, enter:

```python
gui.send_ttl(channel = 5, state = 1)
```

To send a TTL "OFF" event, enter:

```python
gui.send_ttl(channel = 5, state = 0)
```
