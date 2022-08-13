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
        - save and close the GUI
    
    To use, first create a OpenEphysHTTPServer object:
        
        >> gui = OpenEphysHTTPServer()
        
    Then, change or query the GUI's state via object properties and methods:
        
        >> gui.acquire(10) # Acquire data for 10 seconds 
        
        >> gui.status()
        Response: { "mode" : "ACQUIRE" }
        
        >> gui.record(3600) # Record data for 1 hour
        
        >> gui.status()
        Response: { "mode" : "RECORD" }
        
        >> gui.idle() # Stop acquisition and recording
        
        >> gui.status()
        Response: { "mode" : "IDLE" }
    
    """

    def __init__(self, address='http://127.0.0.1:37497'):
        
        """ 
        Construct an OpenEphysHTTPServer object

        Parameters
        ----------
        address : String
            Defines the base URL address.
        """
        
        self.address = address

    def send(self, url, payload=None):

        """
        Send a request to the server.

        Parameterss
        ----------
        url : String
            The URL to send the request to.
        payload : Dictionary
            The payload to send with the request.
        """

        try: 

            if payload is None:
                resp = requests.get(url)
            else:
                resp = requests.put(url, data = json.dumps(payload))

        except requests.exceptions.Timeout:
            # Maybe set up for a retry, or continue in a retry loop
            print("Timeout")
        except requests.exceptions.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            print("Bad URL")
        except requests.exceptions.RequestException as e:
            # OpenEphys server needs to be enabled
            print("OpenEphys HttpServer likely not enabled")
            raise SystemExit(e)

        return resp.json()

    def load(self, cfg_path):

        """
        Load a configuration file.

        Parameters
        ----------
        cfg_path : String
            The path to the configuration file.
        """

        payload = { 
            'path' : cfg_path
        }
        url = self.address + '/api/load'
        res = self.send(url, payload)
        time.sleep(1)
        return res

    def get_processors(self, filter_by_name=""):

        """
        Get the list of processors.

        Parameters
        ----------
        filter_by_name : String
            Filter the list by processor name.
        """

        url = self.address + '/api/processors'
        data = self.send(url)
        if filter_by_name == "":
            return data
        else:
            return [x for x in data['processors'] if x['name'] == filter_by_name]

    def get_param(self, pid, sid):

        """
        Get parameters for a stream.

        Parameters
        ----------
        pid : Integer
            The processor ID.
        sid : Integer
            The stream ID.
        """

        url = self.address + '/api/processors/' + str(pid) + '/streams/' + str(sid) + '/parameters'
        data = self.send(url)
        return data

    def set_param(self, pid, sid, param_name, val):

        """
        Set parameters for a stream.

        Parameters
        ----------
        pid : Integer
            The processor ID.
        sid : Integer
            The stream ID.
        param_name : String
            The parameter name.
        val : Any
            The parameter value (must match the parameter type).
        """

        url = self.address + '/api/processors/' + str(pid) + '/streams/' + str(sid) + '/parameters/' + param_name
        payload = {
            'value' : val
        }
        data = self.send(url, payload)
        return data

    # Get current recording information
    def get_recording_info(self, key=""):

        """
        Get recording information.

        Parameters
        ----------
        key : String
            The key to get.
        """

        url = self.address + '/api/recording'
        data = self.send(url)
        if key == "":
            return data
        elif key in data:
            return data[key]
        else:
            return "Invalid key"


    def set_parent_dir(self, path):

        """
        Set the parent directory.

        Parameters
        ----------
        path : String
            The path to the parent directory.
        """

        url = self.address + '/api/recording'
        payload = {
            'parent_directory' : path
        }
        data = self.send(url, payload)
        return data

    def set_prepend_text(self, text):

        """
        Set the prepend text.

        Parameters
        ----------
        text : String
            The text to prepend.
        """

        url = self.address + '/api/recording'
        payload = {
            'prepend_text' : text
        }
        data = self.send(url, payload)
        return data

    def set_base_text(self, text):

        """
        Set the base text.

        Parameters
        ----------
        text : String
            The text to base name of the recording directory (see GUI docs).
        """

        url = self.address + '/api/recording'
        payload = {
            'base_text' : text
        }
        data = self.send(url, payload)
        return data

    def set_append_text(self, text):

        """
        Set the append text.

        Parameters
        ----------
        text : String
            The text to append.
        """

        url = self.address + '/api/recording'
        payload = {
            'append_text' : text
        }
        data = self.send(url, payload)
        return data

    def set_file_path(self, node_id, file_path):

        """
        Set the file path.

        Parameters
        ----------
        node_id : Integer
            The node ID.
        file_path : String
            The file path.
        """

        url = self.address + '/api/processors/' + str(node_id) + '/config'
        payload ={ 
            'text' : file_path
        }
        data = self.send(url, payload)
        return data

    def set_file_index(self, node_id, file_index):

        """
        Set the file index.

        Parameters
        ----------
        node_id : Integer
            The node ID.
        file_index : Integer
            The file index.
        """

        url = self.address + '/api/processors/' + str(node_id) + '/config'
        payload ={ 
            'text' : file_index
        }
        data = self.send(url, payload)
        return data

    def set_record_engine(self, node_id, engine):

        """
        Set the record engine for a record node.

        Parameters
        ----------
        node_id : Integer
            The node ID.
        engine : Integer
                The record engine index.
        """

        url = self.address + '/api/processors/' + str(node_id) + '/config'
        payload = { 
            'text' : engine
        }
        data = self.send(url, payload)
        return data

    def set_record_path(self, node_id, directory):

        """
        Set the record path.

        Parameters
        ----------
        node_id : Integer
            The node ID.
        directory : String
            The record path.
        """

        url = self.address + '/api/recording/' + str(node_id)
        payload ={ 
            'parent_directory' : directory
        }
        data = self.send(url, payload)
        return data

    def acquire(self, duration=0):

        """
        Acquire data.

        Parameters
        ----------
        duration : Integer
            The duration in seconds.
        """

        url = self.address + '/api/status'
        payload = { 
            'mode' : 'ACQUIRE',
        }
        data = self.send(url, payload)
        if duration: time.sleep(duration)
        return data

    def record(self, duration=0):

        """
        Record data.

        Parameters
        ----------
        duration : Integer
            The duration in seconds.
        """

        url = self.address + '/api/status'
        payload = { 
            'mode' : 'RECORD',
        }
        data = self.send(url, payload)
        if duration: time.sleep(duration)
        return data

    def idle(self, duration=0):

        """
        Stop acquiring/recording data.

        Parameters
        ----------
        duration : Integer
            The duration in seconds.
        """

        url = self.address + '/api/status'
        payload = { 
            'mode' : 'IDLE',
        }
        data = self.send(url, payload)
        if duration: time.sleep(duration)
        return data

    def quit(self):

        """
        Quit the GUI.
        """

        url = self.address + '/api/window'
        payload = { 
            'command' : 'quit' 
        }
        data = self.send(url, payload)
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
        print(list_of_files)
        while count > 0:
            latest_file = max(list_of_files, key=os.path.getctime)
            latest_recordings.append(os.path.join(directory, latest_file))
            list_of_files.remove(latest_file)
            count -= 1
        return latest_recordings