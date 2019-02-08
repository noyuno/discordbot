from http.server import BaseHTTPRequestHandler, HTTPServer
import asyncio
import discord
import json
import os
import queue
import socket
import sys
import threading
import time
from datetime import datetime
import schedule

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
            s = self.rfile.read(int(self.headers.get('content-length'))).decode('utf-8')
            got = json.loads(s)
            sendqueue.put(got)
            res = { 'status': 200 }
        except Exception as e:
            err = e.with_traceback(sys.exc_info()[2])
            res = { 'status': 500, 'type': err.__class__.__name__, 'message': str(err) }
            print('error: {0}({1}), got: {2}'.format(err.__class__.__name__, str(err), got))
        self.send_response(res['status'])
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode('utf-8'))

def httpserver(loop):
    asyncio.set_event_loop(loop)
    print('launch http server')
    server = HTTPServer(('discordbot', 80), APIHandler)
    server.serve_forever()

def scheduler(loop):
    asyncio.set_event_loop(loop)
    print('launch scheduler')
    schedule.every().day.at('22:30').do( # 07:30
        (lambda: sendqueue.put({ 'message': datetime.now().strftime('おはようございます') })))
    schedule.every().day.at('09:20').do( # 18:20
        (lambda: sendqueue.put({ 'message': datetime.now().strftime('夕ごはんの時間です') })))

    while True:
        schedule.run_pending()
        time.sleep(1)

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
        await self.channel.send('hello this is k2/discordbot')

    async def on_message(self, message):
        try:
            if message.author == self.user:
                return
            if message.content.startswith('hi'):
                await message.channel.send('hi')
            if "天気" in message.content:
                await message.channel.send('not implemented yet')
                #await weather()
        except Exception as e:
            err = e.with_traceback(sys.exc_info()[2])
            err = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
            print(err)
            sendqueue.put({'message': err})


    async def send_task(self):
        await self.wait_until_ready()
        # wait login
        while (not self.is_ready()) or (self.channel is None):
            await asyncio.sleep(1)
        # main loop
        # this loop must catch exception
        while not self.is_closed():
            try:
                await asyncio.sleep(1)
                if not self.sendqueue.empty():
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
                    if q.get('filename') is not None:
                        await self.channel.send_file(q.get('filename'))
                    if anyembed:
                        await self.channel.send(q.get('message'), embed=e)
                    else:
                        await self.channel.send(q.get('message'))

                    print('sent message {0} to channel {1}'.format(q, self.channel.name))
            except Exception as e:
                err = e.with_traceback(sys.exc_info()[2])
                print('error: {0}({1})'.format(err.__class__.__name__, str(err)))

def main():
    global sendqueue

    if os.environ.get('DISCORD_TOKEN') is None:
        print('DISCORD_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    if os.environ.get('DISCORD_CHANNEL_NAME') is None:
        print('DISCORD_CHANNEL_ID is not set', file=sys.stderr)
        sys.exit(1)

    print('listen at {0}'.format(socket.gethostbyname_ex(socket.gethostname())))

    httploop = asyncio.new_event_loop()
    threading.Thread(target=httpserver, args=(httploop,)).start()

    scheduleloop = asyncio.new_event_loop()
    threading.Thread(target=scheduler, args=(scheduleloop,)).start()

    print('launch discord client')
    #client = discord.Client()
    #@client.event
    #async def on_ready():
    #    print('We have logged in as {0.user}'.format(client))
    #@client.event
    #async def on_message(message):
    #    if message.author == client.user:
    #        return

    #    if message.content.startswith('hi'):
    #        await message.channel.send('Hello!')
    client = DiscordClient(os.environ.get('DISCORD_CHANNEL_NAME'), sendqueue)
    client.run(os.environ.get('DISCORD_TOKEN'))

if __name__ == '__main__':
    main()

