# An HTTP server designed to make testing easy
import sys
import os
import os.path as path
import stat
import signal
import atexit
import pickle
import httplib
from time import sleep
from BaseHTTPServer import BaseHTTPRequestHandler
from SocketServer import TCPServer
import httplib

RESPONSE_DIR = path.join(path.abspath(os.path.dirname(__file__)), 'responses')
RESPONSE_PATH = path.join(RESPONSE_DIR, 'current_response.pkl')
LAST_REQUEST_PATH = path.join(RESPONSE_DIR, 'last_request.pkl')
server_pid = None

class ServerAlreadyRunning(Exception):
    pass

def log(message):
    logfile = open(path.join(RESPONSE_DIR, 'server.log'), 'a')
    print >> logfile, message
    logfile.close()

def server_info(port, pid=None):
    if pid is None:
        pid = server_pid
    return "(pid: %s, port: %s)" % (str(pid), str(port))

def spawn(port=8888):
    """spawns an instance of the HTTP test server as a child process"""
    global server_pid

    if server_pid is not None:
        log("server already running " + server_info(port))
        raise ServerAlreadyRunning(server_info(port))
    else:
        log("spawning server on port " + str(port))

    if not path.exists(RESPONSE_DIR):
        os.mkdir(RESPONSE_DIR)

    pid = os.fork()
    if pid == 0: # in child process
        os.execl(sys.executable, sys.executable, __file__, str(port))
    else: # in parent process
        server_pid = pid
        atexit.register(kill)
        wait_for_server_to_start(5, 1, port)
        return server_pid

def wait_for_server_to_start(retries, poll_interval, port):
    if retries == 0:
        msg = '\nHTTP test server taking too long to start - aborting test!'
        print >> sys.stderr, msg
        kill()
        os._exit(1)

    c = httplib.HTTPConnection('localhost:' + str(port))
    try:
        c.connect()
    except:
        sleep(poll_interval)
        wait_for_server_to_start(retries - 1, poll_interval, port)
    else:
        c.close()


def run_server(port=8888):
    # Prevents server output from showing up in our test runner output.
    logfile = open(path.join(RESPONSE_DIR, 'server.log'), 'a')
    os.dup2(logfile.fileno(), 2)
    logfile.close()

    TCPServer.allow_reuse_address = True
    try:
        httpd = TCPServer(('', port), HttpTestRequestHandler)
        log("http_test_server running " + server_info(port, os.getpid()))
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("http_test_server shutting down " + server_info(port, os.getpid()))
        try: httpd.socket.close()
        except: pass
        exit()


def kill():
    """stops this instance of the HTTP test server"""
    global server_pid
    if server_pid is not None:
        log("killing server (pid: %s)" % str(server_pid))
        os.kill(server_pid, signal.SIGINT)
        os.wait() # beware of zombies
    else:
        log("server not running")
    server_pid = None

def set_response(**kwargs):
    """sets the response returned for all HTTP requests"""
    method = 'ANY'
    if 'method' in kwargs:
        method = kwargs['method'].upper()
        del kwargs['method']

    response = {
        'status': 200,
        'headers': {},
        'body': 'OK'
    }
    response.update(kwargs)
    response = {method: response}

    stored_responses = _read()
    stored_responses.update(response)
    _write(stored_responses)

def clear_responses(**kwargs):
    _write({})

def last_request():
    return _read('request')

def _read(which='response'):
    path = RESPONSE_PATH
    if which == 'request':
        path = LAST_REQUEST_PATH
    f = open(path, 'r')
    result = pickle.load(f)
    f.close()
    return result

def _write(obj, which='response'):
    path = RESPONSE_PATH
    if which == 'request':
        path = LAST_REQUEST_PATH
    f = open(path, 'w')
    result = pickle.dump(obj, f)
    f.close()


class HttpTestRequestHandler(BaseHTTPRequestHandler):
    """
    serves the response in 'tests/helpers/resonses/current_response.txt'
    regardless of the request method or paramters.
    """

    def do_response(self, http_method):
        global last_request, last_response

        if not path.exists(RESPONSE_PATH):
            set_response()

        response = _read()
        _write({
            'server': str(self.server),
            'path': str(self.path),
            'method': str(self.command),
            'headers': dict(self.headers)
        }, 'request')

        if http_method in response:
            response = response[http_method]
        else:
            response = response['ANY']

        self.send_response(response['status'])
        for k, v in response['headers'].items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(response['body'])

        sleep(0.005)
        # Throttle request to avoid 'Connection reset by peer' errors. This
        # error seems to be happening because the server is closing the
        # connection before the client has a chance to read the response body.

    def do_GET(self):
        self.do_response('GET')

    def do_POST(self):
        self.do_response('POST')

    def do_PUT(self):
        self.do_response('PUT')

    def do_DELETE(self):
        self.do_response('DELETE')

if __name__ == '__main__':
    port = 8888
    if len(sys.argv) == 2:
        try: port = int(sys.argv[1])
        except ValueError: pass
    run_server(port)
