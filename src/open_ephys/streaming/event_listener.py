"""
MIT License

Copyright (c) 2020 Open Ephys

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import zmq
import json

def default_spike_callback(info):
    """
    Code to run when a spike event is received.

    Parameters
    ----------
    info - dict 

    """

    return

def default_ttl_callback(info):
    """
    Code to run when a TTL event is received.

    Parameters
    ----------
    info - dict 

    """

    return


class EventListener:

    """
    A class that communicates with the Open Ephys Event Broadcaster plugin.
    
    See: https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Event-Broadcaster.html
    for more info.
    
    It can be used to receive TTL events and spike times over a network connection.

    IMPORTANT: The Event Broadcaster must be configured to send events in "JSON" format.
    
    To use, first create an EventListener object:
        
        >> stream = EventListener()
        
    Then, define a callback function for TTL events, spikes, or both:
        
        >> def ttl_callback_function(event_info):
            # how should the program respond to the incoming event?
        
    Finally, start the stream to listen for events.
        
        >> stream.start(ttl_callback = ttl_callback_function)

    This will call your desired function whenever a new event is received.
    
    """

    def __init__(self, ip_address = '127.0.0.1',
                 port = 5557):
        
        """ Construct an EventListener object

        Parameters
        ----------
        ip_address : string
            IP address of the computer running the GUI
            Defaults to localhost
        port : int
            The port of the Event Broadcaster plugin to be controlled
            Defaults to 5557
        
        """
        
        self.url = "tcp://%s:%d" % (ip_address, port)

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.url)
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')

        print("Initialized EventListener at " + self.url)


    def start(self, 
        ttl_callback = default_ttl_callback,
        spike_callback = default_spike_callback):

        """
        Starts the listening process, with separate callbacks
        for TTL events and spikes.

        The callback functions should be of the form:

          function(info)

        where `info` is a Python dictionary.

        See the README file for the dictionary contents.

        """

        print("Starting EventListener")

        while True:
            try:
                parts = self.socket.recv_multipart()

                if len(parts) == 2:

                    info = json.loads(parts[1].decode('utf-8'))

                    if info['event_type'] == 'spike':
                        spike_callback(info)
                    else:
                        ttl_callback(info)

            except KeyboardInterrupt:
                print()  # Add final newline
                break