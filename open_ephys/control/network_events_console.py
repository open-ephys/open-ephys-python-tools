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
import sys

raw_input = input

def run(hostname='localhost', port=5556):
    
    with zmq.Context() as ctx:
        with ctx.socket(zmq.REQ) as sock:
            sock.connect('tcp://%s:%d' % (hostname, port))
            sock.RCVTIMEO = int(100);
            while True:
                try:
                    message = raw_input('>> ')
                    
                    if message in ['q','quit','exit','quit()']:
                        break
                    
                    sock.send_string(message)
                    response = sock.recv_string()
                    print(response)
                    
                except EOFError:
                    print()  # Add final newline
                    break


if __name__ == '__main__':
    
    print('\nAvailable commands: \n' + 
          '--------------------\n' +
          
          'StartAcquisition\n' + 
          'StopAcquisition\n' + 
          'StartRecording\n' + 
          'StopRecording\n\n' + 

          'Available queries: \n' +
          '-------------------\n'
          
          'IsAcquiring\n' + 
          'IsRecording\n\n' + 
          
          'Send a TTL event: \n' +
          '---------------------\n' + 
          'TTL Channel=1 on=1\n' + 
          'TTL Channel=1 on=0\n\n'
          
          'To exit, enter "q", "quit", or "exit"\n'
          )
    
    if len(sys.argv) == 2:
        if sys.argv[1].find('.') > -1 or sys.argv[1] == 'localhost':
            run(hostname=sys.argv[1])
        else:
            run(port=int(sys.argv[1]))
    elif len(sys.argv) == 3:
        run(hostname=sys.argv[1],
            port=int(sys.argv[2]))
    else:
        run()
