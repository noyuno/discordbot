import os
import sys
import discord
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import asyncio
import queue

sendqueue = queue.Queue()

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('content-type', 'text')
        self.end_headers()
        self.wfile.write('discordbot'.encode('utf-8'))


    def do_POST(self):
        global sendqueue
        res = { 'status': 0, 'type': 'none', 'message': 'none' }
        got = { }
        try:
            s = self.rfile.read(int(self.headers.get('content-length'))).decode("utf-8")
            got = json.loads(s)
            sendqueue.put(got)
            res = { 'status': 200 }
        except Exception as e:
            err = e.with_traceback(sys.exc_info()[2])
            res = { 'status': 500, 'type': err.__class__.__name__, 'message': str(err) }
            print("error: {0}({1}), got: {2}".format(err.__class__.__name__, str(err), got))
        self.send_response(res['status'])
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode('utf-8'))

def httpserver(loop):
    asyncio.set_event_loop(loop)
    print('launch http server')
    server = HTTPServer(("discordbot", 80), APIHandler)
    server.serve_forever()

class DiscordClient(discord.Client):
    def __init__(self, channelname, sendqueue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.send_task())
        self.channelname = channelname
        self.channel = None
        self.sendqueue = sendqueue

    async def on_ready(self):
        print('logged in as {0.user}'.format(self))
        self.channel = [channel for channel in self.get_all_channels() if channel.name == self.channelname][0]
        await self.channel.send('hello this is discordbot')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('hi'):
            print('hi')
            await message.channel.send('hi')

    async def send_task(self):
        await self.wait_until_ready()
        # wait login
        while (not self.is_ready()) or (self.channel is None):
            await asyncio.sleep(1)
        # main loop
        # this loop must catch exception
        while not self.is_closed():
            try:
                q = self.sendqueue.get()
                e = discord.Embed()
                anyembed = False
                if q.get('title') is not None:
                    e.title = q.get('title')
                    anyembed = True
                if q.get('description') is not None:
                    e.description = q.get('description')
                    anyembed = True
                if q.get('url') is not None:
                    e.url = q.get('url')
                    anyembed = True
                if q.get('color') is not None:
                    e.color = q.get('color')
                    anyembed = True
                if q.get('image') is not None:
                    e.set_image(url=q.get('image'))
                    anyembed = True
                if q.get('thumbnail') is not None:
                    e.set_image(url=q.get('thumbnail'))
                    anyembed = True
                if q.get('video') is not None:
                    e.set_image(url=q.get('video'))
                    anyembed = True
                if anyembed:
                    await self.channel.send(q.get('message'), embed=e)
                else:
                    await self.channel.send(q.get('message'))

                print("sent message {0} to channel {1}".format(q, self.channel.name))
                self.sendqueue.task_done()
            except Exception as e:
                err = e.with_traceback(sys.exc_info()[2])
                print("error: {0}({1})".format(err.__class__.__name__, str(err)))

def main():
    global sendqueue

    if os.environ.get('DISCORD_TOKEN') is None:
        print('DISCORD_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    if os.environ.get('DISCORD_CHANNEL_NAME') is None:
        print('DISCORD_CHANNEL_ID is not set', file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    threading.Thread(target=httpserver, args=(loop,)).start()

    print('launch discord client')
    client = DiscordClient(os.environ.get('DISCORD_CHANNEL_NAME'), sendqueue)
    print('trying login...')
    client.run(os.environ.get('DISCORD_TOKEN'))

if __name__ == '__main__':
    main()

