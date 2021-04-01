# `open_ephys.streaming`

This module makes it possible to listen to events from the [Open Ephys GUI](https://open-ephys.org/gui) via a Python process, either running locally or over a network.

Your GUI's signal chain must include a [Event Broadcaster](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html) plugin in order for this module to work. The Event Broadcaster must be configured to send events in "Header/JSON" format.

## Usage

### Initialization

First, load the module:

```python
from open_ephys.streaming import EventListener
```

To listen for events coming from an Open Ephys instance running on the same machine, simply enter:

```python
stream = EventListener()
```

To specify a custom IP address or port number, use:

```python
stream = EventListener(ip_address = '10.127.50.1',
                     port = 5558)
```

### Defining callbacks

Whenever the `EventListener` receives an event, it checks if it's a TTL event or a spike, and then sends a dictionary containing event info to the specified callback function, e.g.:

```python
def ttl_callback(info):
    if info['channel'] == 2 and info['data'] == True:
        print('Rising event on channel 2')

```

The TTL callback should be designed to handle a Python dictionary with the following contents:

```
{
  'channel': int, 
  'type': 'ttl', 
  'data': bool, 
  'timing': 
  {
    'sampleRate': int, 
    'timestamp': int
  }, 
  'identifier': str, 
  'name': str, 
  'metaData': { dict }
}
```

The spike callback should be designed to handle a Python dictionary with the following contents:

```
{
  'type': 'spike', 
  'sortedID': int, 
  'numChannels': int, 
  'threshold': list, 
  'timing': 
  {
    'sampleRate': int, 
    'timestamp': int
  }, 
  'identifier': string, 
  'name': string, 
  'metaData': 
  {
    'Color': list
  }
}
```

### Starting and stopping event listening

To start listening, enter:

```python
stream.start(ttl_callback=ttl_callback,
             spike_callback=spike_callback)
```

To stop listening, press `ctrl-C`.
