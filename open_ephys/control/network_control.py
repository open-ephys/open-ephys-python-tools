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
import time

class NetworkControl:
    
    """
    A class that communicates with the Open Ephys NetworkEvents plugin
    
    See: https://github.com/open-ephys-plugins/NetworkEvents for more info.
    
    It can be used to start/stop acquisition, start/stop recording, and 
    send TTL events to an instance of the Open Ephys GUI, either locally
    or over a network connection.
    
    To use, first create a NetworkControl object:
        
        >> gui = NetworkControl()
        
    Then, change or query the GUI's state via object properties and methods:
        
        >> gui.start 
        Response: StartedAcquisition
        
        >> gui.is_acquiring
        True
        
        >> gui.record
        Response: StartedRecording
        
        >> gui.is_recording
        True
        
        >> gui.send_ttl(channel = 5, state = 1)
        Response: TTLHandled: Channel=5 on=1
        
        >> gui.stop
        Response: StoppedAcquisition
    
    """
    
    def __init__(self, ip_address = '127.0.0.1',
                 port = 5556):
        
        """ Construct a NetworkControl object

        Parameters
        ----------
        ip_address : string
            IP address of the computer running the GUI
            Defaults to localhost
        port : int
            The port of the NetworkEvents plugin to be controlled
            Default to 5556
        
        """
        
        self.url = "tcp://%s:%d" % (ip_address, port)
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.RCVTIMEO = int(1000);
        self.socket.connect(self.url)
        
    @property
    def start(self):
        """Start data acquisition"""
        self.socket.send_string('StartAcquisition')
        self._get_response()
        
    @property
    def stop(self):
        """Stop data acquisition"""
        self.socket.send_string('StopAcquisition')
        self._get_response()
        
    @property
    def record(self):
        """Start recording"""
        self.socket.send_string('StartRecord')
        self._get_response()
        
    @property
    def start_recording(self): # alias
        """Start recording (alias for NetworkControl.record)"""
        self.record
        
    @property
    def stop_recording(self):
        """Stop recording"""
        self.socket.send_string('StopRecord')
        self._get_response()
        
    @property
    def is_recording(self):
        """Get recording state (True/False)"""
        self.socket.send_string('IsRecording')
        return self.socket.recv().decode('utf-8') == "1"
    
    @property
    def is_acquiring(self):
        """Get acquisition state (True/False)"""
        self.socket.send_string('IsAcquiring')
        return self.socket.recv().decode('utf-8') == "1"
        
    def send_ttl(self, channel=1, state=1):
        """Trigger a TTL event
        
         Parameters
        ----------
        channel : int
            Channel number (1-8)
        state : int or bool
            Event state (on = 1/True, off = 0/False)
        
        """
        if state:
            self.socket.send_string('TTL Channel=' + str(channel) + " on=1")
        else:
            self.socket.send_string('TTL Channel ' + str(channel) + " on=0")
        self._get_response()
        
    def wait(self, time_in_seconds):
        """
        Waits for a certain number of seconds
        
        Parameters
        ----------
        time_in_seconds : int or float
            Amount of time to wait

        """
        
        time.sleep(time_in_seconds)
        
    def _get_response(self):
        print('Response: ' + self.socket.recv().decode('utf-8'))

    #@property
    # NO LONGER IMPLEMENTED IN GUI
    #def record_to_new_directory(self):
    #    self.socket.send_string('StartRecord CreateNewDir=1')
    #    self.get_response()
    #
      
    # NO LONGER IMPLEMENTED IN GUI
    #def get_recording_path(self):
    #   self.socket.send_string('GetRecordingPath')
    #   return self.socket.recv().decode('utf-8')

    # Some additional commands:
    #
    #start_cmd = 'StartRecord'
    #
    #rec_dir = os.path.join(os.getcwd(), 'Output_RecordControl')
    #
    #commands = [start_cmd + ' RecDir=%s' % rec_dir,
    #            start_cmd + ' PrependText=Session01 AppendText=Condition01',
    #            start_cmd + ' PrependText=Session01 AppendText=Condition02',
    #            start_cmd + ' PrependText=Session02 AppendText=Condition01',
    #            start_cmd,
    #            start_cmd + ' CreateNewDir=1']
    
# %%