from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import asyncio
import sys
import socket

def makeAPIHandler(sendqueue, logger):
    class APIHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super(APIHandler, self).__init__(*args, **kwargs)

        def do_GET(self):
            self.send_response(200)
            self.send_header('content-type', 'text')
            self.end_headers()
            self.wfile.write('discordbot'.encode('utf-8'))

        def do_POST(self):
            res = { 'status': 0, 'type': 'none', 'message': 'none' }
            got = { }
            try:
                s = self.rfile.read(int(self.headers.get('content-length'))).decode('utf-8')
                got = json.loads(s)
                self.sendqueue.put(got)
                res = { 'status': 200 }
            except Exception as e:
                err = e.with_traceback(sys.exc_info()[2])
                res = { 'status': 500, 'type': err.__class__.__name__, 'message': str(err) }
                self.logger.error('error: {0}({1}), got: {2}'.format(err.__class__.__name__, str(err), got))
            self.send_response(res['status'])
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
    ret = APIHandler
    ret.sendqueue = sendqueue
    ret.logger = logger
    return ret

class API():
    def __init__(self, loop, sendqueue, logger):
        self.loop = loop
        self.sendqueue = sendqueue
        self.logger = logger

    def run(self):
        asyncio.set_event_loop(self.loop)
        handler = makeAPIHandler(self.sendqueue, self.logger)
        server = HTTPServer(('discordbot', 80), handler)
        self.logger.debug('listen api at {0}'.format(socket.gethostbyname_ex(socket.gethostname())))
        server.serve_forever()

