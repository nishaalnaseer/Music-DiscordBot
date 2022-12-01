import json
import os
import socket
from tkinter import messagebox
import vlc
import time
import tkinter as tk
from threading import Thread
from cryptography.fernet import Fernet

client_version = "0.0.2"


# TODO add comments

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


def play_song(path):
    pass


def receive(client):
    encrypted = client.recv(10024).decode("utf-8")
    decrypted = fernet.decrypt(encrypted)
    print(decrypted.decode("utf-8"))


class Info:
    def __init__(self):
        self.invite = "https://discord.com/api/oauth2/authorize?client_id=1045040579295334511&permissions" \
                      "=1634269132864&scope=bot "
        self.token = "MTA0NTA0MDU3OTI5NTMzNDUxMQ.G06YTn.9xUg4n1BpmL0yz9s1CQtLkYFmn56hiQ713n8uY"
        self.key = "yIrHbGSEhXnSd_as_R30Uo0R8fy2X6kCnSNZiT76cTQ="


class VlcPlayer:
    def __init__(self):
        self.current_track: vlc.MediaPlayer = vlc.MediaPlayer("D:\\Misc\\Songs\\Organised\\How U Like Me Now.m4a")
        self.initialise = False

    def resume(self, args):
        self.current_track.play()

    def play(self, track_index):
        self.current_track.stop()
        song_path = SONG_MAP[int(track_index[1])]
        self.current_track = vlc.MediaPlayer(song_path)
        self.initialise = True
        self.current_track.play()

    def pause(self, args):
        if self.initialise:
            self.current_track.pause()


def set_label(root, theme, text):
    txt_label = tk.Label(root, text=text, bg=theme, font=("consolas", 12), justify='center', pady=30)
    txt_label.grid(columnspan=5)
    return txt_label


def reconnecting(label):
    status = f"Reconnecting to {IP}:{PORT}"
    label.config(text=status)
    time.sleep(1)


def client_func(vlc_player, root, theme):
    global client

    functions = {
        "PLAY": vlc_player.play,
        "RESUME": vlc_player.resume,
        "PAUSE": vlc_player.pause,
        "SKIP": vlc_player.play,
    }
    label = set_label(root, theme, "Hello")

    while not STOP_THREADS:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect((IP, PORT))
            status = f"Connected to {IP}:{PORT}"
            label.config(text=status)
        except ConnectionRefusedError:
            reconnecting(label)
            continue
        except ConnectionResetError:
            reconnecting(label)
            continue
        except ConnectionAbortedError:
            reconnecting(label)
            continue
        except ConnectionError:
            reconnecting(label)
            continue

        while not STOP_THREADS:
            try:
                encrypted = client.recv(10024).decode("utf-8")
                print(encrypted)
            except ConnectionRefusedError:
                reconnecting(label)
                break
            except ConnectionResetError:
                reconnecting(label)
                break
            except ConnectionAbortedError:
                reconnecting(label)
                break
            except ConnectionError:
                reconnecting(label)
                break
            except OSError:
                reconnecting(label)
                break

            decrypted = fernet.decrypt(encrypted).decode("utf-8")
            print(decrypted)
            args = decrypted.split(" ")
            function = functions[args[0]]
            function(args)


def main():
    root = tk.Tk()
    root.geometry("500x250")
    root.title("Rannamaari Client")
    root.configure(bg="powder blue", padx=110, pady=30)
    root.resizable(width=False, height=False)
    current_value = tk.DoubleVar()
    theme = "powder blue"

    def volume_setter():
        volume = slider.get()
        while not STOP_THREADS:
            if volume != slider.get():
                vlc_player.current_track.audio_set_volume(slider.get())
                time.sleep(0.1)
            time.sleep(0.4)

    def on_closing():
        global STOP_THREADS, client
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # STOP_THREADS = True
            # time.sleep(1)
            client.close()
            root.destroy()
            os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=3)

    # label for the slider
    slider_label = tk.Label(root, text='Volume', bg=theme)

    slider_label.grid(column=0, row=0, sticky='w', pady=50)

    #  slider
    slider = tk.Scale(
        root,
        from_=0,
        to=100,
        orient='horizontal',  # vertical
        bg="powder blue",
        # command=slider_changed,
        variable=current_value
    )

    slider.grid(column=1, row=0, sticky='we')
    slider.set(44)
    vlc_player = VlcPlayer()
    thread0 = Thread(target=volume_setter)
    thread0.start()

    thread1 = Thread(target=client_func, args=[vlc_player, root, theme])  # connection server
    thread1.start()
    root.mainloop()


if __name__ == '__main__':
    with open("config.json", 'r') as f:
        config = json.load(f)
    fernet = Fernet(config["crypto_key"])
    info = indexing(config["root_music_folder"])
    SONG_MAP = info[0]
    SONGS = info[1]
    NUM_SONGS = len(SONGS)
    IP, PORT = config["ip"], config["port"]

    STOP_THREADS = False
    client: socket.socket = None

    try:
        main()
    except Exception as e:
        print(e)
