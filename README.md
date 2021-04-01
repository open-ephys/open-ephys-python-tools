# Open Ephys Python Tools

<img src="logo.png" width="300" />

## Overview

This repository is meant to centralize and standardize Python-specific tools for interacting with the [Open Ephys GUI](https://github.com/open-ephys/plugin-GUI).

It consists of three modules:

1. `analysis` - loads data in every format supported by the GUI, using a common interface

2. `control` - allows a Python process to control the GUI, locally or over a network connection

3. `streaming` - receives data from the GUI for real-time analysis and visualization in Python

## Installation

From inside a Python virtual environment (`conda` or otherwise), run the following command:

```bash

$ pip install git+https://github.com/open-ephys/open-ephys-python-tools

```

Alternatively, if you've cloned the repository locally, you can run the following command from inside the `open-ephys-python-tools` directory:


```bash

$ pip install .

```
We will eventually add `open-ephys-python-tools` to the [Python Package Index](https://pypi.org/), but we are waiting until the code base is more stable.

## Usage

### analysis

```python

from open_ephys.analysis import Session

directory = '/path/to/data/2020-11-10_09-28-30' # for example

session = Session(directory)
```

If the directory contains data from one more Record Nodes (GUI version 0.5+), the `session` object will contain a list of RecordNodes, accessible via `session.recordnodes[N]`, where `N = 0, 1, 2,`, etc.  

If your directory just contains data (any GUI version), individual recordings can be accessed via `session.recordings`. The format of the recordings will be detected automatically as either 
[Binary](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Binary-format.html), 
[Open Ephys](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Binary-format.html), 
[NWB 1.0](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/NWB-format.html), or 
[KWIK](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/KWIK-format.html).

Each `recording` object has the following fields:

* `continuous` : continuous data for each subprocessor in the recording
* `spikes` : spikes for each electrode group
* `events` : Pandas `DataFrame` of event times and metadata

More details about `continuous`, `spikes`, and `events` objects can be found in the [analysis module README file](open_ephys/analysis/README.md).

### control

First, launch an instance of Open Ephys, and make sure a [Network Events](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html) plugin is in the signal chain.

Then, from your Python process:

```python

from open_ephys.control import NetworkControl

url = '10.128.50.10' # IP address of the computer running Open Ephys

gui = NetworkControl(url)

gui.start # start acquisition

```

More details about available commands can be found in the [control module README file](open_ephys/control/README.md).

### streaming

First, launch an instance of Open Ephys, and make sure a [Event Broadcaster](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html) plugin is in the signal chain.

Then, from your Python process:

```python

from open_ephys.streaming import EventListener

url = '10.128.50.10' # IP address of the computer running Open Ephys

stream = EventListener(url)

```

Next, define a callback function to handle each incoming event:

```python

def ttl_callback(event_info):

    print("Event occurred on channel " 
          + info['channel'] 
          + " at " 
          + info['timing']['timestamp'] / info['timing']['sampleRate'] 
          + " seconds.")

```

Finally, start listening for events by running...

```python

stream.start(ttl_callback=ttl_callback)

```

...and press `ctrl-C` to stop the process.

More details about available commands can be found in the [streaming module README file](open_ephys/streaming/README.md).

## Contributing

This code base is under active development, and we welcome bug reports, feature requests, and external contributions. If you're working on an extension that you think would be useful to the community, don't hesitate to [submit an issue](https://github.com/open-ephys/open-ephys-python-tools/issues).