import threading
import requests
import os
import sys

import util

class Weather():
    def __init__(self, sendqueue, logger):
        self.sendqueue = sendqueue
        self.logger = logger
        self.loc = None
        self.lat = None
        self.lng = None
        (self.loc, self.lat, self.lng) = self.location()

    def run(self, loc=None):
        if loc is not None:
            (lat, lng) = self.location(loc)
        else:
            (loc, lat, lng) = (self.loc, self.lat, self.lng)
        tf = threading.Thread(target=self.forecast, args=(loc, lat, lng))
        tx = threading.Thread(target=self.xrain, args=(loc, lat, lng))
        tf.start()
        tx.start()

    def location(self, loc=None):
        if loc is None:
            loc = os.environ.get('LOCATION')
        if loc == "":
            loc = 'Tokyo'
        url = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}&key={1}'.format(
                loc, os.environ.get('GOOGLE_MAPS_API_KEY'))
        # debug
        self.logger.debug(url)
        r = requests.get(url).json()
        if r['status'] != "OK" or len(r['results']) == 0:
            raise RuntimeError('Weather.location(): Google API returned {}'.format(r['status']))

        lat = r['results'][0]['geometry']['location']['lat']
        lng = r['results'][0]['geometry']['location']['lng']
        # debug
        #self.sendqueue.put({'message': 'lat: {0}, lng: {1}'.format(lat, lng)})
        return (loc, lat, lng)

    def forecast(self, loc, lat, lng):
        try:
            env = ['GOOGLE_MAPS_API_KEY', 'DARK_SKY_API_KEY']
            if util.environ(env, 'warning'):
                self.sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
                return
            url = 'https://api.darksky.net/forecast/{0}/{1},{2}?lang=ja&units=si'.format(
                os.environ.get('DARK_SKY_API_KEY'), str(self.lat), str(self.lng))
            #debug
            self.logger.debug(url)
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
            msg = 'forecast()'
            self.logger.exception(msg, stack_info=True)
            self.sendqueue.put({'message': 'error {}: {}({})'.format(msg, e.__class__.__name__, str(e)) })

    def xrain(self, loc, lat, lng):
        try:
            env = ['XRAIN_ZOOM', 'MANET']
            if util.environ(env, 'warning'):
                self.sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
                return
            # & -> %26
            url = 'http://{0}/?url=http://www.river.go.jp/x/krd0107010.php?lon={1}%26lat={2}%26opa=0.4%26zoom={3}%26leg=0%26ext=0&width=1000&height=850'.format(
                os.environ.get('MANET'), lng, lat, os.environ.get('XRAIN_ZOOM'))
            # debug
            self.logger.debug(url)
            r = requests.get(url)
            if 'image' not in r.headers['content-type']:
                pass
                # error
                self.sendqueue.put({'message': 'could not get screenshot' })
                return
            self.sendqueue.put({ 'imagefile': r.content })
        except Exception as e:
            msg = 'xrain()'
            self.logger.exception(msg, stack_info=True)
            self.sendqueue.put({'message': 'error {}: {}({})'.format(msg, e.__class__.__name__, str(e)) })

