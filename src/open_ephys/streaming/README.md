# `open_ephys.streaming`

This module makes it possible to listen to events from the [Open Ephys GUI](https://open-ephys.org/gui) via a Python process, either running locally or via a network connection.

The GUI's signal chain must include an [Event Broadcaster](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html) plugin in order for this module to work. The Event Broadcaster must be configured to send events in **JSON** format.

## Usage

### Initialization

First, load the module:

```python
from open_ephys.streaming import EventListener
```

To listen for events coming from an Open Ephys GUI instance running on the same machine, create an `EventListener` with no input arguments:

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
    if info['line'] == 2 and info['state']:
        print('Rising event on line 2')

```

The `ttl_callback` should be designed to handle a Python dictionary with the following contents:

```
{
   "event_type" : "ttl",
   "stream" : str,
   "source_node" : int,
   "sample_rate" : float,
   "channel_name" : str,
   "sample_number" : int,
   "line" : int,
   "state" : int
}

```

The `spike_callback` should be designed to handle a Python dictionary with the following contents:

```
{
   "event_type" : "spike",
   "stream" : str,
   "source_node" : int,
   "electrode" : str,
   "num_channels" : int,
   "sample_rate" : float,
   "sample_number" : int,
   "sorted_id" : int,
   "amp1" : float,
   "amp2" : float,
   "amp3" : float,
   "amp4" : float
}

```

### Starting and stopping event listening

To start listening, enter:

```python
stream.start(ttl_callback=ttl_callback,
             spike_callback=spike_callback)
```

To stop listening, press `ctrl-C`.

