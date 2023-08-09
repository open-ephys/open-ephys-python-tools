"""
MIT License

Copyright (c) 2022 Open Ephys

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

import os
import platform
import subprocess

import requests
import json
import time 

import glob

class OpenEphysHTTPServer:
    
    """
    A class that communicates with the Open Ephys HTTP Server 
    
    See: https://open-ephys.github.io/gui-docs/User-Manual/Remote-control.html for more info.
    
    The server can be used to:

        - load configurations
        - get/set processor parameters 
        - start/stop acquisition
        - start/stop recording
        - close the GUI
    
    To use, first create a OpenEphysHTTPServer object:
        
        >> from open_ephys.control import OpenEphysHTTPServer
        >> gui = OpenEphysHTTPServer() # defaults to localhost, optionally specify an IP address
        
    Then, change or query the GUI's state via object properties and methods:

        >> gui.load('/Users/Ephys/Documents/config.xml') # Load a signal chain
        
        >> gui.acquire(10) # Acquire data for 10 seconds and then stop
        
        >> gui.record(3600) # Record data for 1 hour and return to the previous state
        
        >> gui.status() # Get current status ('IDLE', 'ACQUIRE', or 'RECORD')
        'IDLE'
    
    """

    def __init__(self, address='127.0.0.1'):
        
        """ 
        Construct an OpenEphysHTTPServer object

        Parameters
        ----------
        address : String
            Defines the base URL address
            Defaults to 127.0.0.1 (localhost)
        """
        
        self.address = 'http://' + address + ':37497'

    def send(self, endpoint, payload=None):

        """
        Send a request to the server.

        Parameters
        ----------
        endpoint : String
            The API endpoint for the request.
            Must begin with "/api/"
        payload : Dictionary
            The payload to send with the request.
            
            If a payload is specified, a PUT request
            will be used; otherwise it will be a GET request.
        """

        try: 

            if payload is None:
                resp = requests.get(self.address + endpoint)
            else:
                resp = requests.put(self.address + endpoint, 
                                    data = json.dumps(payload))

        except requests.exceptions.Timeout:
            # Maybe set up for a retry, or continue in a retry loop
            print("Timeout")
        except requests.exceptions.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            print("Bad URL")
        except requests.exceptions.RequestException as e:
            # Open Ephys server needs to be enabled
            print("Open Ephys HTTP Server likely not enabled")

        return resp.json()

    def load(self, config_path):

        """
        Load a configuration file.

        Parameters
        ----------
        config_path : String
            The path to the configuration file.
        """

        payload = { 
            'path' : config_path
        }

        res = self.send('/api/load', payload)
        time.sleep(1)
        return res

    def get_processor_list(self):

        """
        Returns all available processors in the GUI's Processor List
        """

        data = self.send('/api/processors/list')
        return [processor["name"] for processor in data['processors']]

    def get_processors(self, filter_by_name=""):

        """
        Get the list of processors.

        Parameters
        ----------
        filter_by_name : String
            Filter the list by processor name.
        """

        data = self.send('/api/processors')
        if filter_by_name == "":
            return data["processors"]
        else:
            return [x for x in data['processors'] if x['name'] == filter_by_name]

    def clear_signal_chain(self):

        """
        Clear the signal chain.
        """

        data = self.send('/api/processors/clear')

        return data

    def add_processor(self, name, source=None, dest=None):

        """
        Add a processor to the signal chain.

        Parameters
        ----------
        name : String
            The name of the processor to add (e.g. "Record Node")
        source : Integer
            The 3-digit processor ID of the source (e.g. 101)
        dest : Integer
            The 3-digit processor ID of the destination (e.g. 102)
        """

        endpoint = '/api/processors/add'
        payload = { 'name' : name }

        # If only processor name is specified, set source to most recently added processor
        if source is None and dest is None:
            if len(self.get_processors()) > 0:
                payload['source_id'] = max(self.get_processors(), key=lambda processor: processor['id'])['id']
        if source is not None:
            payload['source_id'] = source
        if dest is not None:
            payload['dest_id'] = dest

        data = self.send(endpoint, payload)

        return data

    def delete_processor(self, processor_id):

        """
        Delete a processor.

        Parameters
        ----------
        processor_id : Integer
            The 3-digit processor ID (e.g. 101)
        """

        endpoint = '/api/processors/delete'
        payload = {
            'id' : processor_id
        }

        data = self.send(endpoint, payload)

        return data

    def get_parameters(self, processor_id, stream_index):

        """
        Get parameters for a stream.

        Parameters
        ----------
        processor_id : Integer
            The 3-digit processor ID (e.g. 101)
        stream_index : Integer
            The index of the stream (e.g. 0).
        """

        endpoint = '/api/processors/' + str(processor_id) + '/streams/' + str(stream_index) + '/parameters'
        data = self.send(endpoint)

        return data

    def set_parameter(self, processor_id, stream_index, param_name, value):

        """
        Update a parameter value

        Parameters
        ----------
        processor_id : Integer
            The 3-digit processor ID (e.g. 101)
        stream_index : Integer
            The index of the stream (e.g. 0)
        param_name : String
            The parameter name (e.g. low_cut)
        value : Any
            The parameter value (must match the parameter type).
            Hint: Float parameters must be sent with a decimal 
                included (e.g. 1000.0 instead of 1000)

        Returns
        -------

        """

        endpoint = '/api/processors/' + str(processor_id) + '/streams/' + str(stream_index) + '/parameters/' + param_name
        payload = {
            'value' : value
        }
        data = self.send(endpoint, payload)
        return data

    def get_recording_info(self, key=""):

        """
        Get the current recording parameters.

        Available keys:
        - append_text : string that's appended to the directory name
        - base_text : the name of the current recording directory
        - parent_directory : the path where recordings are stored
        - prepend_text : string that's prepended to the directory name
        - record_nodes : a list containing information about available Record Nodes

        Parameters
        ----------
        key : String (optional)
            The specific parameter to return

        Returns
        -------
        info : dict
            All recording parameters, if no key is supplied

        param : String
            The specified parameter value, if a key is supplied

        """

        data = self.send('/api/recording')
        if key == "":
            return data
        elif key in data:
            return data[key]
        else:
            return "Invalid key"

    def set_parent_dir(self, path):

        """
        Set the parent directory for recording.

        This will only be applied to Record Nodes that have
        not yet been added to the signal chain.

        Parameters
        ----------
        path : String
            The path to the parent directory.

        Returns
        -------
        info : dict
            Current recording parameters
        """

        payload = {
            'parent_directory' : path
        }
        data = self.send('/api/recording', payload)
        return data

    def set_prepend_text(self, text):

        """
        Set the prepend text.

        Parameters
        ----------
        text : String
            The text to prepend.

        Returns
        -------
        info : dict
            Current recording parameters
        """

        payload = {
            'prepend_text' : text
        }
        data = self.send('/api/recording', payload)
        return data

    def set_base_text(self, text):

        """
        Set the base text.

        Parameters
        ----------
        text : String
            The text to base name of the recording directory (see GUI docs).

        Returns
        -------
        info : dict
            Current recording parameters
        """

        payload = {
            'base_text' : text
        }
        data = self.send('/api/recording', payload)
        return data

    def set_append_text(self, text):

        """
        Set the append text.

        Parameters
        ----------
        text : String
            The text to append.

        Returns
        -------
        info : dict
            Current recording parameters
        """

        payload = {
            'append_text' : text
        }
        data = self.send('/api/recording', payload)
        return data

    def set_start_new_dir(self):

        """
        Toggles the creation of a new directory for the next recording.

        Returns
        -------
        info : dict
            Current recording parameters
        """

        payload = {
            'start_new_directory': "true"
        }
        data = self.send('/api/recording', payload)
        return data

    def set_file_path(self, node_id, file_path):

        """
        Set the file path of a File Reader.

        Parameters
        ----------
        node_id : Integer
            The node ID of the File Reader
        file_path : String
            The file path.

        Returns
        -------
        message : String
            Response message
        """

        endpoint = '/api/processors/' + str(node_id) + '/config'
        payload ={ 
            'text' : file_path
        }
        data = self.send(endpoint, payload)
        return data

    def set_file_index(self, node_id, file_index):

        """
        Set the file index of a File Reader

        Parameters
        ----------
        node_id : Integer
            The node ID of the File Reader
        file_index : Integer
            The file index.

        Returns
        -------
        message : String
            Response message
        """

        endpoint = '/api/processors/' + str(node_id) + '/config'
        payload ={ 
            'text' : file_index
        }
        data = self.send(endpoint, payload)
        return data

    def set_record_engine(self, node_id, engine):

        """
        Set the record engine for a Record Node.

        Parameters
        ----------
        node_id : Integer
            The node ID of the Record Node
        engine : Integer
                The record engine index.
        """

        endpoint = '/api/processors/' + str(node_id) + '/config'
        payload = { 
            'text' : engine
        }
        data = self.send(endpoint, payload)
        return data

    def set_record_path(self, node_id, directory):

        """
        Set the record path for a Record Node

        Parameters
        ----------
        node_id : Integer
            The node ID of the Record Node
        directory : String
            The record path.
        """

        payload ={ 
            'parent_directory' : directory
        }
        data = self.send('/api/recording/' + str(node_id), payload)
        return data

    def status(self):

        """
        Returns the current status of the GUI (IDLE, ACQUIRE, or RECORD)

        """
        return self.send('/api/status')['mode']

    def acquire(self, duration=0):

        """
        Start acquisition.

        Parameters
        ----------
        duration : Integer (optional)
            The acquisition duration in seconds. If given, the
            GUI will acquire data for the specified interval
            and then stop.

            By default, acquisition will continue until it
            is stopped by another command.

        Returns
        -------
        The current status of the GUI after the command returns.

        """

        payload = { 
            'mode' : 'ACQUIRE',
        }
        
        data = self.send('/api/status', payload)
        
        if duration: 
            time.sleep(duration)
            payload = { 
                'mode' : 'IDLE',
            }
            data = self.send('/api/status', payload)
        
        return data['mode']

    def record(self, duration=0):

        """
        Record data.

        Parameters
        ----------
        duration : Integer (optional)
            The acquisition duration in seconds. If given, the
            GUI will record data for the specified interval
            and then return to its previous state.

            By default, recording will continue until it
            is stopped by another command.
        """

        previous_mode = self.status()

        payload = { 
            'mode' : 'RECORD',
        }
        data = self.send('/api/status', payload)
        
        if duration: 
            time.sleep(duration)
            payload = { 
                'mode' : previous_mode,
            }
            data = self.send('/api/status', payload)
        
        return data['mode']

    def idle(self, duration=0):

        """
        Stop acquiring or recording data. 

        Parameters
        ----------
        duration : Integer
            The duration in seconds. If given, the
            GUI will idle for the specified interval
            and then return to its previous state.

            By default, this command will stop
            acquisition/recording and return immediately.
        """

        previous_mode = self.status()

        payload = { 
            'mode' : 'IDLE',
        }
        data = self.send('/api/status', payload)
        if duration: 
            time.sleep(duration)
            payload = { 
                'mode' : previous_mode,
            }
            data = self.send('/api/status', payload)
        
        return data['mode']

    def message(self, message):

        """
        Broadcast a message to all processors during acquisition

        Parameters
        ----------
        message : String
            The message to send.

        Returns
        -------
        message : String
            Response message
        """

        payload = {
            'text' : message
        }
        data = self.send('/api/message', payload)

        return data

    def config(self, node_id, message):

        """
        Send a configuration message to a specific processor

        Parameters
        ----------
        node_id : int
            3-digit node ID for the target processor

        message : String
            The message to send.

        Returns
        -------
        message : String
            Response message
        """

        payload = {
            'text' : message
        }
        data = self.send(f'/api/processors/{node_id}/config', payload)

        return data

    def quit(self):

        """
        Quit the GUI.
        """

        payload = { 
            'command' : 'quit' 
        }
        data = self.send('/api/window', payload)

        return data

    def get_latest_recordings(self, directory, count=1):

        """
        Get the latest recordings.

        Parameters
        ----------
        directory : String
            The directory to search.
        count : Integer
            The number of recordings to return.
        """
        latest_recordings = []
        list_of_files = glob.glob(os.path.join(directory, '**'))

        while count > 0 and len(list_of_files) > 0:
            latest_file = max(list_of_files, key=os.path.getctime)
            latest_recordings.append(os.path.join(directory, latest_file))
            list_of_files.remove(latest_file)
            count -= 1
        return latest_recordings