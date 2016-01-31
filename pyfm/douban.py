# -*- coding: utf-8 -*-
import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:43.0) Gecko/20100101 Firefox/43.0"}


class APIError(Exception):
    pass


class Douban:

    """ Douban class, provides some APIs.
    """

    def __init__(self, email, password, user_id=None, expire=None, token=None, user_name=None, cookies=None):
        self.login_url = 'http://douban.fm/j/login'
        self.channel_url = 'https://www.douban.com/j/app/radio/channels'
        self.api_url = 'http://douban.fm/j/mine/playlist'
        self.app_name = 'radio'
        self.version = '100'
        self.type_map = {
            'new': 'n',
            'playing': 'p',
            'rate': 'r',
            'unrate': 'u',
            'end': 'e',
            'bye': 'b',
            'skip': 's',
        }

        self.email = email
        self.password = password
        self.user_id = user_id
        self.expire = expire
        self.token = token
        self.user_name = user_name
        self.cookies = cookies

        self.logged_in = False
        self.channels = None

    def requests_url(self, ptype, channel_id, **data):
        """
        这里包装了一个函数,发送post_data
        :param ptype: n 列表无歌曲,返回新列表
                      e 发送歌曲完毕
                      b 不再播放,返回新列表
                      s 下一首,返回新的列表
                      r 标记喜欢
                      u 取消标记喜欢
        """
        options = {
            'type': ptype,
            'pt': '3.1',
            'channel': channel_id,
            'pb': '128',
            'from': 'mainsite',
            'r': ''
        }
        if 'sid' in data:
            options['sid'] = data['sid']
        url = 'http://douban.fm/j/mine/playlist'
        s = requests.get(url, params=options,
                         cookies=self.cookies, headers=HEADERS)
        return s

    @staticmethod
    def get_captcha_id():
        try:
            r = requests.get('http://douban.fm/j/new_captcha', headers=HEADERS)
            return r.text.strip('"')
        except Exception as e:
            raise APIError('get_captcha_id error ' + e)

    @staticmethod
    def get_capthca_pic(captcha_id=None):
        options = {
            'size': 'm',
            'id': captcha_id
        }
        r = requests.get('http://douban.fm/misc/captcha',
                         params=options,
                         headers=HEADERS)
        if r.status_code == 200:
            path = '/tmp/captcha_pic.jpg'
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        else:
            print "get_captcha_pic " + r.status_code

    @staticmethod
    def get_captcha_solution():
        import webbrowser
        captcha_id = Douban.get_captcha_id()
        Douban.get_capthca_pic(captcha_id)
        url = "file:///tmp/captcha_pic.jpg"
        webbrowser.open(url)
        captcha_solution = raw_input('Solution:')
        return captcha_id, captcha_solution

    def do_login(self):
        # Has cookies already. No need to login again.
        if self.cookies:
            self.logged_in = True
            return True, None
        self.captcha_id, self.captcha_solution = Douban.get_captcha_solution()
        payload = {'alias': self.email,
                   'form_password': self.password,
                   'source': self.app_name,
                   'captcha_id': self.captcha_id,
                   'captcha_solution': self.captcha_solution,
                   'task': 'sync_channel_list',
                   }
        r = requests.post(self.login_url, data=payload, headers=HEADERS)
        data = r.json()
        if data['r'] == 0:
            self.user_name = data['user_info']['name']
            self.user_id = data['user_info']['uid']
            self.expire = None
            self.token = None
            self.cookies = r.cookies.get_dict()
            self.logged_in = True
            return True, None
        else:
            return False, r.json()['err_msg']

    def _get_type(self, option):
        return self.type_map[option]

    def get_channels(self):
        """ Return a list of channels
        """
        if self.channels is None:
            r = requests.get(self.channel_url, headers=HEADERS)
            # Cache channels
            channels = r.json()['channels']
            if self.logged_in:
                # No api for this.
                # We have to manually add this.
                heart = {u'seq_id': -3,
                         u'name_en': u'Heart',
                         u'abbr_en': u'Heart',
                         u'name': u'红心兆赫',
                         u'channel_id': -3}
                channels.insert(0, heart)
            self.channels = channels
            return self.channels
        else:
            return self.channels

    def get_new_play_list(self, channel, kbps=64):
        _type = self._get_type('new')
        r = self.requests_url(_type, channel)
        if r.json()['r'] == 0:
            songs = r.json()['song']
            return songs

    def get_playing_list(self, sid, channel, kbps=64):
        _type = self._get_type('playing')
        r = self.requests_url(_type, channel, sid=sid)
        if r.json()['r'] == 0:
            songs = r.json()['song']
            return songs

    def rate_song(self, sid, channel):
        _type = self._get_type('rate')
        r = self.requests_url(_type, channel, sid=sid)
        if r.json()['r'] == 0:
            return True, None
        else:
            return False, r.json()['err']

    def unrate_song(self, sid, channel):
        _type = self._get_type('unrate')
        r = self.requests_url(_type, channel, sid=sid)
        if r.json()['r'] == 0:
            return True, None
        else:
            return False, r.json()['err']

    def skip_song(self, sid, channel):
        _type = self._get_type('skip')
        r = self.requests_url(_type, channel, sid=sid)
        if r.json()['r'] == 0:
            return True, None
        else:
            return False, r.json()['err_msg']

    def end_song(self, sid, channel):
        _type = self._get_type('end')
        r = self.requests_url(_type, channel, sid=sid)
        if r.json()['r'] == 0:
            return True, None
        else:
            return False, r.json()['err']

    def bye_song(self, sid, channel):
        """No longer play this song
        """
        _type = self._get_type('bye')
        r = self.requests_url(_type, sid=sid)
        if r.json()['r'] == 0:
            return True, None
        else:
            return False, r.json()['err']
