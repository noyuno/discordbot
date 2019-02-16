import requests
import shutil
import sys
import os
import threading

import util

class Monitoring():
    def __init__(self, sendqueue):
        self.sendqueue = sendqueue
        self.running_last_period = {}

    def run(self, show_all):
        tp = threading.Thread(target=self.dockerps, args=(show_all,))
        td = threading.Thread(target=self.df, args=(show_all,))
        tp.start()
        td.start()

    def dockerps(self, show_all):
        try:
            env = ['CADVISOR', 'CONTAINERS']
            if util.environ(env, 'warning'):
                self.sendqueue.put({'message': 'error: One or some environment variables are not set. Must be set {0}'.format(' '.join(env)) })
                return

            watch_container = {}
            for c in os.environ.get('CONTAINERS').split(','):
                watch_container[c] = False
                if self.running_last_period.get(c) is None:
                    self.running_last_period[c] = True
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
                    flag = util.emoji('ok') if v else util.emoji('bad')
                    text += '{0} {1}\n'.format(flag, k)
                self.sendqueue.put({ 'message': '{0}'.format(text) })
            else:
                text = ''
                count = 0
                for k, v in watch_container.items():
                    if v == False and self.running_last_period.get(k) == True:
                        text += '{0} '.format(k)
                        count += 1
                if count > 0:
                    self.sendqueue.put({ 'message': '{0} {1} が停止しています'.format(util.emoji('bad'), text) })
        except Exception as e:
            err = e.with_traceback(sys.exc_info()[2])
            err = 'error: {0}({1})'.format(err.__class__.__name__, str(err))
            print(err, file=sys.stderr)
            self.sendqueue.put({'message': err})

    def df(self, show_all):
        stat = shutil.disk_usage("/")
        show = False
        message = util.emoji('ok')
        if (stat.used / stat.total > 0.9 and running_last_period.get('df') is None):
            show = True
            message = '{0} ストレージに十分な空き領域がありません\n'.format(util.emoji('bad'))
        if show_all or show:
            self.sendqueue.put({ 'message': '''{0} total: {1}GiB, used: {2}GiB, free: {3}GiB, {4}%'''.format(message,
                        int(stat.total / 1024 / 1024 / 1024),
                        int(stat.used / 1024 / 1024 / 1024),
                        int(stat.free / 1024 / 1024 / 1024),
                        int(stat.used / stat.total * 100))})
            self.running_last_period['df'] = True
