# -*- coding: utf-8 -*-
from collections import defaultdict
from threading import Thread
import subprocess
import logging
from kuwo.Net import (
    get_nodes,
    get_radio_songs,
    get_song_link

)

from .netease_api import Netease


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:43.0) Gecko/20100101 Firefox/43.0"}


logger = logging.getLogger()
netease = Netease()


class APIError(Exception):
    pass


class Kuwo:

    """ Kuwo class, provides some APIs.
    """

    def __init__(self, email, password,
                 user_id=None, expire=None,
                 token=None, user_name=None,
                 cookies=None, use_163=True):

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
        self.use_163 = use_163
        self.logged_in = True
        self.channels = None
        self.get_channels()
        self.channel_songs = {}
        self.channel_cur = defaultdict(lambda: -1)

    @staticmethod
    def get_song_length(song_link):
        # bad idea!
        for _ in range(3):
            cmd = 'mplayer -vo null -ao null -frames 0 -identify {}| grep ID_LENGTH'.format(
                song_link)
            logger.debug(cmd)
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            line = p.stdout.readline().decode()
            if line:
                logger.debug(line)
                length = float(line.split('=')[1])
                return length
        else:
            return 0

    def dig_songs_length(self):
        for i in self.songs:
            if i['length'] <= 0:
                i['length'] = self.get_song_length(i['url'])

    def change_songs_to_douban(self, song):
        douban_song = {
            u'aid': u'',
            u'album': u'',
            u'albumtitle': u'',
            u'alert_msg': u'',
            u'artist': u'',
            u'file_ext': u'mp4',
            u'kbps': u'128',
            u'length': -1,
            u'like': 1,
            u'picture': u'',
            u'sha256': u'',
            u'sid': u'707644',
            u'singers': [{u'id': u'5791',
                          u'is_site_artist': False,
                          u'name': u'\u4e45\u77f3\u8b72',
                          u'related_site_id': 0}],
            u'ssid': u'f40a',
            u'status': 0,
            u'subtype': u'',
            u'title': u'',
            u'url': u''
        }
        douban_song['title'] = song['name']
        douban_song['artist'] = song['artist']
        douban_song['aid'] = song['rid']
        douban_song['sid'] = song['rid']
        if self.use_163:
            song_link, bitrate = netease.get_url_and_bitrate(song['name'])
        else:
            path_exists, song_link, song_path = get_song_link(
                song, {'audio': 3, 'song-dir': '/tmp'})
        douban_song['url'] = song_link
        return douban_song

    def get_radio_songs(self, channel):
        self.channel_cur[channel] += 1
        songs = get_radio_songs(self.channels[channel]['seq_id'],
                                self.channel_cur[channel])
        self.songs = []
        for i in songs:
            self.songs.append(
                self.change_songs_to_douban(i)
            )
        return self.songs

    def do_login(self):
        # Has cookies already. No need to login again.
        return True, None

    def _get_type(self, option):
        return self.type_map[option]

    def get_channels(self):
        """ Return a list of channels
        """
        if self.channels is None:
            self.channels = []
            radios, page = get_nodes(8, 0)
            for i, value in enumerate(radios):
                item = {
                    u'seq_id': value['sourceid'].split(',')[0],
                    u'name_en': value['name'],
                    u'abbr_en': value['disname'],
                    u'name': value['name'],
                    u'channel_id': i,
                }
                self.channels.append(item)
            return self.channels
        else:
            return self.channels

    def get_new_play_list(self, channel, kbps=64):
        songs = self.get_radio_songs(channel)
        if songs:
            return songs

    def get_playing_list(self, sid, channel, kbps=64):
        return self.get_cur_song()

    def rate_song(self, sid, channel):
        return True, None

    def unrate_song(self, sid, channel):
        return True, None

    def skip_song(self, sid, channel):
        return True, None

    def end_song(self, sid, channel):
        return True, None

    def bye_song(self, sid, channel):
        """No longer play this song
        """
        return True, None
