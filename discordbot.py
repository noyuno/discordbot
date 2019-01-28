import os
import sys
import discord
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

channelname = ''
client = None

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('content-type', 'text')
        self.end_headers()
        self.wfile.write('discordbot'.encode('utf-8'))

    def do_POST(self):
        global client, channelid
        res = { 'status': 0, 'message': 'none' }
        try:
            got = json.loads(self.rfile.read(int(self.headers.get('content-length')))
                             .decode('utf-8'))
            channel = [channel for channel in client.get_all_channels() if channel.name == channelname][0]
            channel.send(got['message'])
            print("sent message {0} to channel {1}".format(got['message'], channel.name))
            res = { 'status': 200 }
        except Exception as e:
            mes = e.with_traceback(sys.exc_info()[2])
            res = { 'status': 500, 'message': mes }
            print("error: {0}, got: {1}".format(mes, got))
        self.send_response(res['status'])
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode('utf-8'))

def httpserver():
    print('launch http server')
    server = HTTPServer(("discordbot", 80), APIHandler)
    server.serve_forever()

def main():
    global client, channelname

    if os.environ.get('DISCORD_TOKEN') is None:
        print('DISCORD_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    if os.environ.get('DISCORD_CHANNEL_NAME') is None:
        print('DISCORD_CHANNEL_ID is not set', file=sys.stderr)
        sys.exit(1)

    channelname = os.environ.get('DISCORD_CHANNEL_NAME')

    threading.Thread(target=httpserver).start()

    print('launch discord client')
    client = discord.Client()

    print('trying login...')
    
    @client.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(client))
        channel = [channel for channel in client.get_all_channels() if channel.name == channelname][0]
        channel.send('hello this is discordbot')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        if message.content.startswith('hi'):
            print('hi')
            await message.channel.send('hi')

    client.run(os.environ.get('DISCORD_TOKEN'))

if __name__ == '__main__':
    main()

