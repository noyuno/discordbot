import asyncio
import threading
import os
import sys
import queue
import schedule
import socket
import time

import util
import discordbot
import api
import weather
import monitoring

class Scheduler():
    def __init__(self, sendqueue, weather, monitoring):
        self.sendqueue = sendqueue
        self.weather = weather
        self.monitoring = monitoring

    def run(self, loop):
        asyncio.set_event_loop(loop)
        print('launch scheduler')
        schedule.every().day.at('22:30').do(self.good_morning) # 07:30
        schedule.every().day.at('09:20').do( # 18:20
            (lambda: self.sendqueue.put({ 'message': '夕ごはんの時間です' })))
        schedule.every(5).minutes.do(self.monitoring.run, show_all=False)

        while True:
            schedule.run_pending()
            time.sleep(1)

    def good_morning(self):
        self.sendqueue.put({ 'message': 'おはようございます'})
        self.weather.run()

def main():
    envse = ['DISCORD_TOKEN', 'DISCORD_CHANNEL_NAME']
    envsc = ['LOCATION', 'XRAIN_LON', 'XRAIN_LAT', 'XRAIN_ZOOM', 'MANET',
             'GOOGLE_MAPS_API_KEY', 'DARK_SKY_API_KEY', 'CADVISOR', 'CONTAINERS']

    f = util.environ(envse, 'error')
    util.environ(envsc, 'warning')
    if f:
        print('error: some environment variables are not set. exiting.', file=sys.stderr)
        sys.exit(1)

    sendqueue = queue.Queue()

    print('listen at {0}'.format(socket.gethostbyname_ex(socket.gethostname())))
    httploop = asyncio.new_event_loop()
    threading.Thread(target=api.run, args=(httploop,sendqueue)).start()

    wea = weather.Weather(sendqueue)
    mon = monitoring.Monitoring(sendqueue)
    sched = Scheduler(sendqueue, wea, mon)
    scheduleloop = asyncio.new_event_loop()
    threading.Thread(target=sched.run, args=(scheduleloop,)).start()

    print('launch discord client')
    client = discordbot.DiscordClient(os.environ.get('DISCORD_CHANNEL_NAME'), sendqueue, wea, mon)
    client.run(os.environ.get('DISCORD_TOKEN'))

if __name__ == '__main__':
    main()

