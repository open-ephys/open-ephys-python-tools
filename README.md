# Open Ephys Python Tools

<img src="https://user-images.githubusercontent.com/200366/199058390-f18efb8e-9012-4efe-b32d-309ef92b730d.png" width="300" />

## Overview

This package centralizes and standardizes Python-specific tools for interacting with the [Open Ephys GUI](https://github.com/open-ephys/plugin-GUI).

It consists of three modules:

1. [`analysis`](https://github.com/open-ephys/open-ephys-python-tools/tree/main/src/open_ephys/analysis) - loads data in every format supported by the GUI, using a common interface

2. [`control`](https://github.com/open-ephys/open-ephys-python-tools/tree/main/src/open_ephys/control) - allows a Python process to control the GUI, locally or over a network connection

3. [`streaming`](https://github.com/open-ephys/open-ephys-python-tools/tree/main/src/open_ephys/streaming) - receives data from the GUI for real-time analysis and visualization

## Installation

Inside a Python virtual environment (`conda` or otherwise), run the following command:

```bash

$ pip install open-ephys-python-tools

```

Alternatively, if you've cloned the repository locally, you can run the following command from inside the `open-ephys-python-tools` directory:


```bash

$ pip install -e .

```

*Note:* The `-e` argument links the package in the original location (rather than by copying), so any edits to the source code can be used immediately. This is optional but can be extremely useful for debugging.

## Usage

### [`analysis`](https://github.com/open-ephys/open-ephys-python-tools/tree/main/src/open_ephys/analysis)

```python

from open_ephys.analysis import Session

directory = '/path/to/data/2020-11-10_09-28-30' # for example

session = Session(directory)
```

If the directory contains data from one more Record Nodes, the `session` object will contain a list of Record Nodes, accessible via `session.recordnodes[N]`, where `N = 0, 1, 2,`, etc.  

If your directory just contains data (e.g. you specified a Record Node directory), individual recordings can be accessed via `session.recordings`. The format of the recordings will be detected automatically as either 
[Binary](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Binary-format.html), 
[Open Ephys](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Open-Ephys-format.html), or
[NWB 2](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/NWB-format.html).

*Note:* This package is intended for use with data saved by Open Ephys GUI version `0.6.x` and higher. However, the `Binary` format is backwards-compatible with data saved by version `0.5.x`. To read data saved in Open Ephys, NWB 1.0, or Kwik formats by GUI version `0.5.x` and lower, you can use code in the `archive` branch of this repository.

Each `recording` object has the following fields:

* `continuous` : continuous data for each subprocessor in the recording
* `spikes` : spikes for each electrode group
* `events` : Pandas `DataFrame` of event times and metadata

More details about `continuous`, `spikes`, and `events` objects can be found in the [analysis module README file](https://github.com/open-ephys/open-ephys-python-tools/blob/main/src/open_ephys/analysis/README.md).

### [`control`](https://github.com/open-ephys/open-ephys-python-tools/tree/main/src/open_ephys/control)

First, launch an instance of the Open Ephys GUI (version `0.6.0` or higher).

Then, from your Python process:

```python

from open_ephys.control import OpenEphysHTTPServer

address = '10.128.50.10' # IP address of the computer running Open Ephys

gui = OpenEphysHTTPServer(address)

gui.acquire(10) # acquire data for 10 seconds

```

More details about available commands can be found in the [control module README file](https://github.com/open-ephys/open-ephys-python-tools/blob/main/src/open_ephys/control/README.md).

### [`streaming`](https://github.com/open-ephys/open-ephys-python-tools/tree/main/src/open_ephys/streaming)

First, launch an instance of the Open Ephys GUI and make sure an [Event Broadcaster](https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html) plugin is in the signal chain.

Then, from your Python process:

```python

from open_ephys.streaming import EventListener

address = '10.128.50.10' # IP address of the computer running Open Ephys

stream = EventListener(address)

```

Next, define a callback function to handle each incoming event:

```python

def ttl_callback(info):

    print("Event occurred on TTL line " 
          + info['line'] 
          + " at " 
          + info['sample_number'] / info['sample_rate'] 
          + " seconds.")

```

Finally, start listening for events by running...

```python

stream.start(ttl_callback=ttl_callback)

```

...and press `ctrl-C` to stop the process.

More details about available commands can be found in the [streaming module README file](https://github.com/open-ephys/open-ephys-python-tools/blob/main/src/open_ephys/streaming/README.md).

## Contributing

This code base is under active development, and we welcome bug reports, feature requests, and external contributions. If you're working on an extension that you think would be useful to the community, don't hesitate to [submit an issue](https://github.com/open-ephys/open-ephys-python-tools/issues).