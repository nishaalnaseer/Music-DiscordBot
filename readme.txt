Do the following for client and server seperately

create a config.json file in server with the following keys

{
  "file_types":  ['.mp3'], # file extensions to be indexed on startup 
  "root_music_folder": "", # path of root music folder
  "ip": "127.0.0.1", # server ip
  "port": , # server port
  "max_clients": 5, # max clients accepted by server
  "token": "", # authentication token of discord bot
  "crypto_key": "" # server-client communication is encrypted use a common key here
}

for client create a config.json without max_clients and token, everything else is essential for client

1. extract the zip file into a folder of their own
2. open cmd and create a virtual env
3. activate enviroment
3. enter the following into command line 'pip install -r requirements.txt'
4. for server run main.py file, for client run client.py file