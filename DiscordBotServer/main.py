import discord
import os
import threading
import socket
import time
from cryptography.fernet import Fernet
import json
import mutagen
import math
from multiprocessing import Process

server_version = "0.0.4"


# TODO add comments
# TODO separate server completely from Bot class
# TODO separate Bot.control_flow from the class, in a way that all Bot() instances can be put there.

def print_help(args):
    return "HELLO! I'm Rannamari, a Coop music player. Im still in dev-phase so please mock my flaws.\n" \
           "The following are my commands. I hope you understand them lol.\n\n" \
           "1. 'help' to display this.\n\n2. seek: to search for a track. f'seek {phrase}' and it may " \
           "return all songs that has the phrase in its file name.\n\n3. saw: First use seek function, and when the " \
           "list of songs is returned use f'saw {index_in_returned_list} add/play'. If you add 'add' to the end of " \
           "the string the corresponding track will be added to the tail or bottom of the queue/playlist, if you add " \
           "'play' the corresponding track will be added to top or head of the queue/playlist.\n\n" \
           "4. list: 'list' to list all items in queue/playlist. \n\n5. remv: Syntex: f'remv {index_in_playlist} to " \
           "remove a track from queue/playlist'\n\n6. cls: 'cls' to clear queue/playlist. \n\n7. skip: 'skip' to skip" \
           "current track. \n\n8. now: 'now' to display currently playing track and its progress.\n\n9. puse: 'puse' " \
           "to pause \n\n10. resm: 'resm' to resume."


def update_file():
    with open("playlist.json", 'w') as f:
        json.dump({0: PLAYLIST}, f)


def indexing(path):
    file_types = config["file_types"]
    index = {}
    songs = []

    if os.name == "nt":
        slash = "\\"
    else:
        slash = "/"

    num = 0

    def search_folders(folder_path, num):
        items = os.listdir(folder_path)
        folders = []
        for ii in range(len(items)):
            file = items[ii]
            file_path = f"{folder_path}{slash}{file}"
            if os.path.isdir(file_path):
                folders.append(file_path)
                continue

            split = os.path.splitext(file)
            if split[1] in file_types:
                songs.append(split[0])
                index.update({num: file_path})
                num += 1

        for folder in folders:
            num = search_folders(folder, num)

        return num

    search_folders(path, 0)
    return [index, songs]


def list_playlist(args):
    if len(PLAYLIST) == 0:
        return "Nothing in the current playlist"
    string = return_song_description(PLAYLIST) + "\nTo remove enter f'remv {list_index}'"
    return string


def return_song_description(array):
    string = ""
    for index, key in enumerate(array):
        file_path = SONG_MAP[key]
        file = mutagen.File(file_path)
        duration = math.ceil(file.info.length)
        string += f"{index}. {SONGS[key]} - {secs_to_mins(duration)}\n"
    return string


def send_clients(message):
    encrypted = FERNET.encrypt(message.encode())
    for client_info in CLIENTS:
        client = client_info[0]
        try:
            client.send(encrypted)
        except ConnectionRefusedError:
            CLIENTS.remove(client_info)
        except ConnectionResetError:
            CLIENTS.remove(client_info)
        except ConnectionAbortedError:
            CLIENTS.remove(client_info)
        except ConnectionError:
            CLIENTS.remove(client_info)


def secs_to_mins(duration) -> str:
    seconds = math.ceil(duration % 59)
    minutes = math.floor(duration / 60)

    if seconds < 10:
        seconds = f"0{seconds}"
    return f"{minutes}:{seconds} "


class Bot(object):
    """docstring for BOT"""

    def __init__(self):
        self.discord_client: discord.Client = None
        self.channel = None
        self.options = []
        self.searched = False
        self.listed = False
        self.arg0_responses = {
            "seek": self.search,
            "saw ": self.saw,
            "list": list_playlist,
            "remv": self.remove,
            "cls": self.clear,
            "skip": self.skip,
            "now": self.status,
            "resm": self.resume,
            "puse": self.pause
        }

        #  music control flow
        self.paused = True
        self.first_track = True
        self.start = 0
        self.duration = 0
        self.time_elapsed = 0
        self.paused_at = 0
        self.total_pause_duration = 0
        self.ever_paused = False
        process = threading.Thread(target=self.control_flow)
        process.start()
        # process.join()

        SERVER.bind((IP, PORT))
        SERVER.listen(MAX_CLIENTS)
        print(f"Listening on {IP}:{PORT}")
        thread = threading.Thread(target=self.run_discord_bot)
        thread.start()
        # run_discord_bot()

        while True:
            try:
                client, addr = SERVER.accept()
                CLIENTS.append([client, addr])
                print(f"Connected to {addr[0]}")
            except Exception as e:
                print(e)
                continue

    def run_discord_bot(self):
        self.client = discord.Client(intents=discord.Intents.all())

        @self.client.event
        async def on_ready():
            print(f"{self.client.user} is now running")

        @self.client.event
        async def on_message(message):
            # Make sure bot doesn't get stuck in an infinite loop
            self.channel = message.channel
            if message.author == self.client.user:
                return

            if type(message.channel) == discord.channel.DMChannel:
                return

            # Get data about the user
            username = str(message.author)
            user_message = str(message.content)
            channel = str(message.channel)

            print(f"{username} said {user_message} on {channel}")

            # send_clients(f"{username} said {user_message} on {channel}")
            await self.send_message(message, user_message)

        self.client.run(config["token"])

    async def send_message(self, message, user_message):
        # response = self.handle_responses(user_message)
        # await message.channel.send(f"```{response}```")
        try:
            response = self.handle_responses(user_message)
            await message.channel.send(f"```{response}```")
            # message.channel
        except discord.errors.HTTPException as e:
            await message.channel.send(f"```The response exceeds 4000 character, please be more specific```")
        # except Exception as e:
        #     print(e)

    def handle_responses(self, message) -> str:
        p_message = message.lower()
        args = [p_message[:4], p_message[4:]]

        if args[0] == "help":
            return print_help(args)
        func = self.arg0_responses[args[0]]
        response = func(args)

        self.searched = args[0] == "seek" or (args[0] == "saw " and self.searched)
        self.listed = args[0] == "list" or (args[0] == "remv" and self.listed)
        return response

    def search(self, args):
        if len(args) != 2 or args[-1] == "":
            return "Type 'help' to display for a guide"

        text = args[1]

        #  eliminate leading spaces infront of text
        i = 0
        for i, letter in enumerate(text):
            if letter != " ":
                break
        text = text[i:]

        lenght = len(text)
        self.options = []
        for index, song in enumerate(SONGS):
            if len(text) > len(song):
                continue

            if song == text:
                self.options.insert(0, index)
                continue

            song = song.lower()
            for start in range(len(song)):
                if song[start:lenght + start] == text:
                    self.options.append(index)
        string = return_song_description(self.options)

        if string == "":
            return "No track that matches your description"

        return string + "\nEnter 'saw' with command 'add'/'play' and the corresponding number"

    def saw(self, args):
        message = args[1]
        new_args = [message[:-4], message[-4:]]
        if not self.searched:
            return "Please seek first"
        if len(args) != 2 or args[0] == "":
            return "Type 'help' to display for a guide"

        try:
            num = int(new_args[0])
            if num < 0:
                raise ValueError
        except ValueError:
            return "Please enter a positive integer"

        if num > len(self.options) - 1:
            return "Integer out of scope"

        option = self.options[num]
        if new_args[1] == " add":
            PLAYLIST.append(option)
            update_file()
            return f"'{SONGS[option]}' has been added to playlist"
        elif new_args[1] == "play":
            PLAYLIST.insert(0, option)
            update_file()

            self.start = time.time()
            self.paused = False
            self.update_duration()
            # print("Actual pause = ", self.paused)  # debugging

            return f"Now playing: '{SONGS[option]}' - at the head of playlist"
        else:
            return "Invalid args"

    def remove(self, args):
        if not self.listed:
            return "Please list first"

        try:
            num = int(args[1])
            if num < 0:
                raise ValueError
        except ValueError:
            return "Please enter a positive integer"

        if num > len(PLAYLIST) - 1:
            return "Integer out of scope"
        if num == 0:
            self.skip(args)

        obj = PLAYLIST[num]
        PLAYLIST.remove(obj)
        update_file()
        return list_playlist(args)

    def status(self, args):
        if self.paused:
            return "Currently paused"
        if len(PLAYLIST) == 0:
            return "There is nothing in playlist"
        index = PLAYLIST[0]
        song = SONGS[index]
        self.update_duration()

        return f"Now playing '{song}' - {secs_to_mins(self.time_elapsed - self.total_pause_duration)} / " \
               f"{secs_to_mins(self.duration)}"

    def update_duration(self):
        index = PLAYLIST[0]
        path = SONG_MAP[index]
        file = mutagen.File(path)
        self.duration = file.info.length

    def pause(self, args):
        if self.paused:
            return "Already paused"
        self.paused_at = time.time()
        self.ever_paused = True
        self.paused = True
        send_clients("PAUSE")
        return "Paused"

    def resume(self, args):
        if len(PLAYLIST) == 0:
            return "Empty playlist, please add some tracks."
        if not self.paused:
            return "A track already playing."
        if self.first_track:
            self.update_duration()
            song = SONGS[PLAYLIST[0]]
            self.paused = False
            self.first_track = False
            self.start = time.time()
            update_file()
            send_clients(f"PLAY {PLAYLIST[0]}")
            return f"Now playing '{song}' - {secs_to_mins(self.time_elapsed - self.total_pause_duration)} / " \
                   f"{secs_to_mins(self.duration)} "

        if self.ever_paused:
            this_duration = time.time() - self.paused_at
        else:
            self.start = time.time()
            this_duration = 0

        self.total_pause_duration += this_duration
        self.paused = False
        self.time_elapsed = time.time() - self.start - self.total_pause_duration

        send_clients("RESUME")
        return self.status(args)

    def skip(self, args):
        PLAYLIST.pop(0)
        song = SONGS[PLAYLIST[0]]

        path = SONG_MAP[PLAYLIST[0]]
        file = mutagen.File(path)
        self.duration = file.info.length
        self.time_elapsed = 0
        self.total_pause_duration = 0
        self.start = time.time()
        self.paused_at = 0
        self.total_pause_duration = 0
        if len(PLAYLIST) == 0:
            self.paused = True

        update_file()
        send_clients("SKIP")
        return f"{song} has been skipped"

    def clear(self, args):
        global PLAYLIST
        PLAYLIST = []
        self.paused = True
        self.start = 0
        self.duration = 0
        self.time_elapsed = 0
        self.paused_at = 0
        self.total_pause_duration = 0
        self.ever_paused = False
        self.first_track = True
        update_file()
        return list_playlist(args)

    def control_flow(self):
        """a function to control the flow of music tracks in playlist, when changing to the next track"""
        global PLAYLIST
        while True:
            time.sleep(1)
            # print(PLAYLIST)  # debug
            if not self.paused:
                self.time_elapsed = time.time() - self.start
                # print(f"{self.duration}, {self.time_elapsed}, {self.total_pause_duration}")  # debug
                # print(self.duration < (self.time_elapsed + 1 - self.total_pause_duration))  # debug
                if self.duration < (self.time_elapsed - self.total_pause_duration):
                    # print("Triggered")  # debug
                    #     self.first_track = False
                    self.duration = 0
                    self.time_elapsed = 0
                    self.total_pause_duration = 0
                    self.paused = False
                    self.first_track = False
                    PLAYLIST.pop(0)
                    update_file()

                    if len(PLAYLIST) == 0:
                        self.paused = True
                        self.first_track = True
                        continue
                    self.start = time.time()

                    self.update_duration()
                    send_clients(f"PLAY {PLAYLIST[0]}")


with open("config.json", 'r') as f:
    config = json.load(f)

songs_info = indexing(config["root_music_folder"])
SONG_MAP = songs_info[0]
SONGS = songs_info[1]
NUM_SONGS = len(SONGS)
with open("playlist.json", 'r') as f:
    playlists = json.load(f)

PLAYLIST = playlists["0"]

FERNET = Fernet(config["crypto_key"])
IP, PORT = config["ip"], config["port"]
MAX_CLIENTS = config["max_clients"]
SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
CLIENTS = []

if __name__ == '__main__':
    Bot()
