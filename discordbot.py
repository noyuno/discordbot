from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import asyncio
import discord
import json
import os
import queue
import requests
import schedule
import shutil
import socket
import sys
import threading
import time

sendqueue = queue.Queue()

running_last_period = {}

emoji_ok = ':white_check_mark:'
emoji_bad = ':red_circle:'

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

def good_morning():
    sendqueue.put({ 'message': 'おはようございます'})
    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(weather())
    weather()

def scheduled_monitoring():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(monitoring(False))

def monitoring(show_all):
    tp = threading.Thread(target=dockerps, args=(show_all,))
    td = threading.Thread(target=df, args=(show_all,))
    tp.start()
    td.start()

def dockerps(show_all):
    global sendqueue, running_last_period

    try:
        env = ['CADVISOR', 'CONTAINERS']
        if check_environ(env, 'warning'):
            sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
            return

        watch_container = {}
        for c in os.environ.get('CONTAINERS').split(','):
            watch_container[c] = False
            if running_last_period.get(c) is None:
                running_last_period[c] = True
        url = 'http://{0}/api/v1.3/containers/docker'.format(os.environ.get('CADVISOR'))
        r = requests.get(url).json()
        #debug
        #print(r['name'])
        for container in r['subcontainers']:
            c = requests.get('http://{0}/api/v1.3/containers{1}'.format(
                os.environ.get('CADVISOR'), container['name'])).json()
            watch_container[c['spec']['labels']['com.docker.compose.service']] = True
        if show_all:
            text = ''
            for k, v in watch_container.items():
                flag = emoji_ok if v else emoji_bad
                text += '{0} {1}\n'.format(flag, k)
            sendqueue.put({ 'message': '{0}'.format(text) })
        else:
            text = ''
            count = 0
            for k, v in watch_container.items():
                if v == False and running_last_period.get(k) == True:
                    text += '{0} '.format(k)
                    count += 1
            if count > 0:
                sendqueue.put({ 'message': '{0} {1} が停止しています'.format(emoji_bad, text) })
    except Exception as e:
        err = e.with_traceback(sys.exc_info()[2])
        err = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
        print(err, file=sys.stderr)
        sendqueue.put({'message': err})

def df(show_all):
    global sendqueue, running_last_period
    stat = shutil.disk_usage("/")
    show = False
    message = emoji_ok
    if (stat.used / stat.total > 0.9 and running_last_period.get('df') is None):
        show = True
        message = '{0} ストレージに十分な空き領域がありません\n'.format(emoji_bad)
    if show_all or show:
        sendqueue.put({ 'message': '''{0} total: {1}GiB, used: {2}GiB, free: {3}GiB, {4}%'''.format(message,
                    int(stat.total / 1024 / 1024 / 1024),
                    int(stat.used / 1024 / 1024 / 1024),
                    int(stat.free / 1024 / 1024 / 1024),
                    int(stat.used / stat.total * 100))})
        running_last_period['df'] = True

def scheduler(loop):
    asyncio.set_event_loop(loop)
    print('launch scheduler')
    schedule.every().day.at('22:30').do(good_morning) # 07:30
    schedule.every().day.at('09:20').do( # 18:20
        (lambda: sendqueue.put({ 'message': '夕ごはんの時間です' })))
    schedule.every().hour.do(scheduled_monitoring)

    while True:
        schedule.run_pending()
        time.sleep(1)

def unixtimestr(ut):
    return datetime.fromtimestamp(
        ut, timezone(timedelta(hours=+9), 'JST')).strftime('%m/%d %H:%M')

def unixtimestrt(ut):
    return datetime.fromtimestamp(
        ut, timezone(timedelta(hours=+9), 'JST')).strftime('%H:%M')

def weather(loc = None):
    tf = threading.Thread(target=forecast, args=(loc,))
    tx = threading.Thread(target=xrain)
    tf.start()
    tx.start()

def forecast(loc = None):
    global sendqueue
    try:
        env = ['GOOGLE_MAPS_API_KEY', 'DARK_SKY_API_KEY']
        if check_environ(env, 'warning'):
            sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
            return

        if loc is None:
            loc = os.environ.get('LOCATION')
        if loc == "":
            loc = 'Tokyo'
        url = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}&key={1}'.format(
                loc, os.environ.get('GOOGLE_MAPS_API_KEY'))
        # debug
        print(url)
        r = requests.get(url).json()
        if r['status'] != "OK" or len(r['results']) == 0:
            # error
            sendqueue.put({'message': r['status']})
            return

        lat = r['results'][0]['geometry']['location']['lat']
        lng = r['results'][0]['geometry']['location']['lng']
        # debug
        #sendqueue.put({'message': 'lat: {0}, lng: {1}'.format(lat, lng)})

        url = 'https://api.darksky.net/forecast/{0}/{1},{2}?lang=ja&units=si'.format(
            os.environ.get('DARK_SKY_API_KEY'), str(lat), str(lng))
        #debug
        print(url)
        r = requests.get(url).json()
        hourly = ''
        count = 0
        for item in r['hourly']['data']:
            count += 1
            if count >= 20:
                break
            if count % 2 == 1:
                continue
            hourly += '{0}: {1}, {2}度, {3}%\n'.format(
                unixtimestrt(item['time']),
                item['summary'],
                int(item['temperature']),
                int(item['precipProbability'] * 100))
        sendqueue.put({'message': '''{0}時点の{1}の天気: {2}, {3}度, 湿度{4}%, 風速{5}m/s
予報: {6}
{7}'''.format(
            unixtimestr(r['currently']['time']),
            loc,
            r['currently']['summary'],
            int(r['currently']['temperature']),
            int(r['currently']['humidity']*100),
            int(r['currently']['windSpeed']),
            r['hourly']['summary'],
            hourly
        )})
    except Exception as e:
        err = e.with_traceback(sys.exc_info()[2])
        err = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
        print(err, file=sys.stderr)
        sendqueue.put({'message': err})

def xrain():
    global sendqueue
    try:
        env = ['XRAIN_LON', 'XRAIN_LAT', 'XRAIN_ZOOM', 'MANET']
        if check_environ(env, 'warning'):
            sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
            return
        # & -> %26
        url = 'http://{0}/?url=http://www.river.go.jp/x/krd0107010.php?lon={1}%26lat={2}%26opa=0.4%26zoom={3}%26leg=0%26ext=0&width=1000&height=850'.format(
            os.environ.get('MANET'), os.environ.get('XRAIN_LON'),
            os.environ.get('XRAIN_LAT'), os.environ.get('XRAIN_ZOOM'))
        # debug
        print(url)
        r = requests.get(url)
        if 'image' not in r.headers['content-type']:
            pass
            # error
            sendqueue.put({'message': 'could not get screenshot' })
            return
        sendqueue.put({ 'imagefile': r.content })
    except Exception as e:
        err = e.with_traceback(sys.exc_info()[2])
        err = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
        print(err, file=sys.stderr)
        sendqueue.put({'message': err})

class DiscordClient(discord.Client):
    def __init__(self, channelname, sendqueue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.send_task())
        self.channelname = channelname
        self.channel = None
        self.sendqueue = sendqueue

    async def on_ready(self):
        print('logged in as {0.user}'.format(self))
        cand = [channel for channel in self.get_all_channels() if channel.name == self.channelname]
        if len(cand) == 0:
            raise Exception("channel {0} not found".format(self.channelname))
        self.channel = cand[0]
        await self.channel.send('hello this is k2/discordbot')

    async def on_message(self, message):
        try:
            if message.author == self.user:
                return
            if message.channel.name != self.channelname:
                return
            if message.content.startswith('hi'):
                await message.channel.send('hi')
            if 'help' in message.content:
                await message.channel.send('available commands: hi, 天気|weather, ps')
            if "天気" in message.content or 'weather' in message.content:
                a = message.content.split(' ')
                if len(a) == 1:
                    weather()
                else:
                    weather(' '.join(a[1:]))
            if 'ps' in message.content:
                monitoring(True)
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
                    fileinstance = None
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
                    if q.get('imagefile') is not None:
                        fileinstance = discord.File(q.get('imagefile'), 'image.png')
                    if anyembed:
                        await self.channel.send(q.get('message'), embed=e, file=fileinstance)
                    else:
                        await self.channel.send(q.get('message'), file=fileinstance)

                    print('sent message data ({0}) to channel {1}'.format(', '.join(q.keys()), self.channel.name))
            except Exception as e:
                err = e.with_traceback(sys.exc_info()[2])
                errtext = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
                print(errtext, file=sys.stderr)
                try:
                    await self.channel.send(errtext)
                except Exception as e:
                    err = e.with_traceback(sys.exc_info()[2])
                    errtext = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
                    print(errtext, file=sys.stderr)


def check_environ(keys, header):
    ret = False
    for k in keys:
        if os.environ.get(k) is None:
            ret = True
            print('{0}: {1} is not set'.format(header, k), file=sys.stderr)
    return ret

def main():
    global sendqueue

    envse = ['DISCORD_TOKEN', 'DISCORD_CHANNEL_NAME']
    envsc = ['LOCATION', 'XRAIN_LON', 'XRAIN_LAT', 'XRAIN_ZOOM', 'MANET',
             'GOOGLE_MAPS_API_KEY', 'DARK_SKY_API_KEY', 'CADVISOR', 'CONTAINERS']


    f = check_environ(envse, 'error')
    check_environ(envsc, 'warning')
    if f:
        print('error: some environment variables are not set. exiting.', file=sys.stderr)
        sys.exit(1)

    print('listen at {0}'.format(socket.gethostbyname_ex(socket.gethostname())))

    httploop = asyncio.new_event_loop()
    threading.Thread(target=httpserver, args=(httploop,)).start()

    scheduleloop = asyncio.new_event_loop()
    threading.Thread(target=scheduler, args=(scheduleloop,)).start()

    print('launch discord client')
    client = DiscordClient(os.environ.get('DISCORD_CHANNEL_NAME'), sendqueue)
    client.run(os.environ.get('DISCORD_TOKEN'))

if __name__ == '__main__':
    main()

