import os
import fcntl
import subprocess
import select
import logging

logger = logging.getLogger()


class Player(object):

    def __init__(self):
        self.is_playing = False
        self.current_song = None
        self.player_process = None
        self.return_code = 0
        self.detect_external_players()

    def detect_external_players(self):
        supported_external_players = [
            ["mplayer", "-slave", "-quiet"],
            ["mpv", "--really-quiet"],
            ["mpg123", "-q"]
        ]

        for external_player in supported_external_players:
            proc = subprocess.Popen(
                ["which", external_player[0]], stdout=subprocess.PIPE)
            env_bin_path = proc.communicate()[0].strip()
            if (env_bin_path and os.path.exists(env_bin_path)):
                self.external_player = external_player
                break

        else:
            print("no supported player found. Exit.")
            raise SystemExit()

    def play(self, song):
        self.current_song = song
        self.player_process = subprocess.Popen(
            self.external_player + [self.current_song.url],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=1, universal_newlines=True
        )
        fcntl.fcntl(self.player_process.stdout.fileno(), fcntl.F_SETFL,
                    fcntl.fcntl(self.player_process.stdout.fileno(),
                                fcntl.F_GETFL) | os.O_NONBLOCK)
        self.is_playing = True

    def perform_command(self, p, cmd, expect, waittime=0.05):
        p.stdin.write(cmd + '\n')  # there's no need for a \n at the beginning
        # give mplayer time to answer...
        while select.select([p.stdout], [], [], waittime)[0]:
            output = p.stdout.readline()
            logger.debug("output: {}".format(output.rstrip()))
            split_output = output.split(expect + '=', 1)
            # we have found it
            if len(split_output) == 2 and split_output[0] == '':
                value = split_output[1]
                return value.rstrip()
        return None

    def get_song_length(self, trycount=100):
        for count in range(trycount):
            ret = self.perform_command(
                self.player_process, 'get_time_length', 'ANS_LENGTH')
            if ret:
                return float(ret)
        else:
            return 0

    def stop(self):
        if self.player_process is None:
            return
        try:
            self.player_process.terminate()
        except:
            pass
