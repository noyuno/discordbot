import threading
import requests
import os
import sys

import util

class Weather():
    def __init__(self, sendqueue):
        self.sendqueue = sendqueue

    def run(self, loc = None):
        tf = threading.Thread(target=self.forecast, args=(loc,))
        tx = threading.Thread(target=self.xrain)
        tf.start()
        tx.start()

    def forecast(self, loc = None):
        try:
            env = ['GOOGLE_MAPS_API_KEY', 'DARK_SKY_API_KEY']
            if util.environ(env, 'warning'):
                self.sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
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
                self.sendqueue.put({'message': r['status']})
                return

            lat = r['results'][0]['geometry']['location']['lat']
            lng = r['results'][0]['geometry']['location']['lng']
            # debug
            #self.sendqueue.put({'message': 'lat: {0}, lng: {1}'.format(lat, lng)})

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
                    util.unixtimestrt(item['time']),
                    item['summary'],
                    int(item['temperature']),
                    int(item['precipProbability'] * 100))
            self.sendqueue.put({'message': '''{0}時点の{1}の天気: {2}, {3}度, 湿度{4}%, 風速{5}m/s
予報: {6}
{7}'''.format(
                util.unixtimestr(r['currently']['time']),
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
            self.sendqueue.put({'message': err})

    def xrain(self):
        try:
            env = ['XRAIN_LON', 'XRAIN_LAT', 'XRAIN_ZOOM', 'MANET']
            if util.environ(env, 'warning'):
                self.sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
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
                self.sendqueue.put({'message': 'could not get screenshot' })
                return
            self.sendqueue.put({ 'imagefile': r.content })
        except Exception as e:
            err = e.with_traceback(sys.exc_info()[2])
            err = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
            print(err, file=sys.stderr)
            self.sendqueue.put({'message': err})

