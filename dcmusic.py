import discord
import os
import asyncio
from youtubesearchpython import VideosSearch
import yt_dlp
from dotenv import load_dotenv
import sqlite3
from contextlib import closing

load_dotenv()

print('bot starts')

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

voice_clients = {}
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

# Dictionary to store playlists for each user or guild
playlists = {}

# Zum Speichern des zuletzt vorgeschlagenen Videos und der zugehörigen Kanal-ID
last_suggestion = {}

# Zum Speichern der Loop-Status für jeden Server
loop_status = {}

# Zum Speichern der Warteschlange für jeden Server
song_queues = {}


# Initialize SQLite database
def init_db():
    with closing(sqlite3.connect('playlists.db')) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS playlists (
                    user_id INTEGER,
                    playlist_name TEXT,
                    song_url TEXT,
                    PRIMARY KEY (user_id, playlist_name, song_url)
                )
            ''')
init_db()


def add_playlist(user_id, playlist_name):
    with closing(sqlite3.connect('playlists.db')) as conn:
        with conn:
            # Check if playlist exists
            cursor = conn.execute('''
                SELECT 1 FROM playlists 
                WHERE user_id = ? AND playlist_name = ?
                LIMIT 1
            ''', (user_id, playlist_name))
            if cursor.fetchone():
                return False
            # Insert dummy entry to create playlist
            conn.execute('''
                INSERT INTO playlists (user_id, playlist_name, song_url)
                VALUES (?, ?, ?)
            ''', (user_id, playlist_name, ''))
            conn.execute('''
                DELETE FROM playlists 
                WHERE user_id = ? AND playlist_name = ? AND song_url = ''
            ''', (user_id, playlist_name))
            return True

def add_to_playlist(user_id, playlist_name, song_url):
    with closing(sqlite3.connect('playlists.db')) as conn:
        with conn:
            conn.execute('''
                INSERT OR IGNORE INTO playlists (user_id, playlist_name, song_url)
                VALUES (?, ?, ?)
            ''', (user_id, playlist_name, song_url))

def get_playlists(user_id):
    with closing(sqlite3.connect('playlists.db')) as conn:
        cursor = conn.execute('''
            SELECT DISTINCT playlist_name FROM playlists 
            WHERE user_id = ?
        ''', (user_id,))
        return [row[0] for row in cursor.fetchall()]

def get_playlist_songs(user_id, playlist_name):
    with closing(sqlite3.connect('playlists.db')) as conn:
        cursor = conn.execute('''
            SELECT song_url FROM playlists 
            WHERE user_id = ? AND playlist_name = ?
        ''', (user_id, playlist_name))
        return [row[0] for row in cursor.fetchall()]

async def search_youtube(query):
    ydl_opts = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"]
        if result:
            video_url = result[0]["webpage_url"]
            return video_url
    return None

async def play_song(voice_client, url, guild_id):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    song = data['url']
    player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

    def after_playing(error):
        if error:
            print(f"Error: {error}")
            return
        if loop_status.get(guild_id):
            # Wenn Loop aktiviert ist, spiele das gleiche Lied erneut ab
            asyncio.run_coroutine_threadsafe(play_song(voice_client, url, guild_id), loop)
        else:
            # Wenn die Warteschlange nicht leer ist, spiele den nächsten Song
            if song_queues[guild_id]:
                next_url = song_queues[guild_id].pop(0)
                asyncio.run_coroutine_threadsafe(play_song(voice_client, next_url, guild_id), loop)
            else:
                # Ansonsten trenne die Verbindung
                asyncio.run_coroutine_threadsafe(voice_client.disconnect(), loop)

    voice_client.play(player, after=after_playing)

@client.event
async def on_ready():
    print(f'{client.user} is now online')

@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignoriere Nachrichten vom Bot selbst

    commands = {
        "suche": ["!suche", "!search", "!find"],
        "confirm": ["!confirm", "!bestätigen"],
        "createplaylist": ["!createplaylist"],
        "addtoplaylist": ["!addtoplaylist"],
        "viewplaylist": ["!viewplaylist"],
        "playplaylist": ["!playplaylist"],
        "play": ["!play", "!spiele"],
        "pause": ["!pause", "!stop"],
        "resume": ["!resume", "!weiter"],
        "skip": ["!skip", "!nextsong", "!überspringen"],
        "exit": ["!exit", "!leave", "!disconnect"],
        "loop": ["!loop", "!repeat", "!wiederholen"],
        "ping": ["!ping", "!test", "!hello"],
        'help': ["!help", "!hilfe"]
    }

    # Search for a song on YouTube
    if any(message.content.startswith(cmd) for cmd in commands["suche"]):
        try:
            args = message.content.split()
            query = ' '.join(args[1:])
            url = await search_youtube(query)

            if url is None:
                await message.channel.send("Kein Ergebnis gefunden.")
            else:
                # Speichere die URL für spätere Verwendung
                last_suggestion[message.channel.id] = url
                await message.channel.send(
                    f"Vorgeschlagenes Video: {url}\nSchreibe `!confirm`, um das Video abzuspielen oder `!addtoplaylist [playlist]` zum Hinzufügen."
                )

        except Exception as e:
            print(e)

    elif any(message.content.startswith(cmd) for cmd in commands["help"]):
        await message.channel.send('look at the documantation at https://github.com/Redstonekey/JMusic')
    elif any(message.content.startswith(cmd) for cmd in commands["ping"]):
        await message.channel.send("THE BOT IS LIVE!")
        await message.channel.send("JMUSIC since 2023")

    # Confirm the suggested video and play it
    elif any(message.content.startswith(cmd) for cmd in commands["confirm"]):
        try:
            url = last_suggestion.get(message.channel.id)
            if not url:
                await message.channel.send(
                    "Kein Video zum Abspielen vorgeschlagen. Bitte nutze `!suche`, um ein Video vorzuschlagen."
                )
                return

            # Überprüfe, ob der Bot im Sprachkanal verbunden ist, und falls nicht, trete dem Sprachkanal bei
            voice_client = voice_clients.get(message.guild.id)
            if not voice_client:
                if message.author.voice and message.author.voice.channel:
                    # Der Bot tritt dem Sprachkanal des Benutzers bei
                    voice_client = await message.author.voice.channel.connect()
                    voice_clients[message.guild.id] = voice_client
                    song_queues[message.guild.id] = []  # Initialisiere die Warteschlange
                else:
                    await message.channel.send(
                        "Du musst in einem Sprachkanal sein, damit der Bot beitreten kann."
                    )
                    return

            # Wenn bereits ein Song abgespielt wird, füge den neuen Song zur Warteschlange hinzu
            if voice_client.is_playing() or voice_client.is_paused():
                song_queues[message.guild.id].append(url)
                await message.channel.send(f"Song zur Warteschlange hinzugefügt: {url}")
            else:
                # Abspielen des vorgeschlagenen Videos
                await play_song(voice_client, url, message.guild.id)

            # Lösche den Vorschlag nach Bestätigung
            del last_suggestion[message.channel.id]

        except Exception as e:
            print(e)

    # Create a new playlist
    elif any(message.content.startswith(cmd) for cmd in commands["createplaylist"]):
        try:
            args = message.content.split()
            playlist_name = ' '.join(args[1:])
            user_id = message.author.id
            
            if add_playlist(user_id, playlist_name):
                await message.channel.send(f"Playlist '{playlist_name}' created.")
            else:
                await message.channel.send(f"Playlist '{playlist_name}' already exists.")

        except Exception as e:
            print(e)

    # Add song to an existing playlist
    elif any(message.content.startswith(cmd) for cmd in commands["addtoplaylist"]):
        try:
            args = message.content.split()
            playlist_name = args[1]
            user_id = message.author.id
            url = last_suggestion.get(message.channel.id)

            if not url:
                await message.channel.send("No song suggested to add. Use `!suche` to suggest a song first.")
                return

            add_to_playlist(user_id, playlist_name, url)
            await message.channel.send(f"Added song to playlist '{playlist_name}'.")

        except Exception as e:
            print(e)

    elif any(message.content.startswith(cmd) for cmd in commands["viewplaylist"]):
        try:
            args = message.content.split()
            playlist_name = ' '.join(args[1:])
            user_id = message.author.id

            songs = get_playlist_songs(user_id, playlist_name)
            if songs:
                await message.channel.send(f"Playlist '{playlist_name}':\n" + "\n".join(songs))
            else:
                await message.channel.send(f"Playlist '{playlist_name}' doesn't exist or is empty.")

        except Exception as e:
            print(e)

    # Play all songs in a playlist
    elif any(message.content.startswith(cmd) for cmd in commands["playplaylist"]):
        try:
            args = message.content.split()
            playlist_name = ' '.join(args[1:])
            user_id = message.author.id

            songs = get_playlist_songs(user_id, playlist_name)
            if not songs:
                await message.channel.send(f"Playlist '{playlist_name}' doesn't exist or is empty.")
                return

            # Rest des Codes bleibt gleich...
            voice_client = voice_clients.get(message.guild.id)
            if not voice_client:
                if message.author.voice and message.author.voice.channel:
                    await message.channel.send(f"Die Playlist {playlist_name} wurde in die Warteschlange hinzugefügt.")
                    voice_client = await message.author.voice.channel.connect()
                    voice_clients[message.guild.id] = voice_client
                    song_queues[message.guild.id] = []
                else:
                    await message.channel.send("You need to be in a voice channel to play music.")
                    return

            song_queues[message.guild.id].extend(songs)

            if not voice_client.is_playing():
                first_song = song_queues[message.guild.id].pop(0)
                await play_song(voice_client, first_song, message.guild.id)

        except Exception as e:
            print(e)

    # Additional commands like pause, resume, skip, etc.
    elif any(message.content.startswith(cmd) for cmd in commands["pause"]):
        try:
            if voice_clients.get(message.guild.id):
                voice_clients[message.guild.id].pause()
        except Exception as e:
            print(e)

    elif any(message.content.startswith(cmd) for cmd in commands["resume"]):
        try:
            if voice_clients.get(message.guild.id):
                voice_clients[message.guild.id].resume()
        except Exception as e:
            print(e)

    elif any(message.content.startswith(cmd) for cmd in commands["skip"]):
        try:
            voice_client = voice_clients.get(message.guild.id)
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                await message.channel.send("Song übersprungen.")
            else:
                await message.channel.send("Es wird aktuell kein Song abgespielt.")
        except Exception as e:
            print(e)

    elif any(message.content.startswith(cmd) for cmd in commands["exit"]):
        try:
            if voice_clients.get(message.guild.id):
                loop_status[message.guild.id] = False  # Deaktiviere Loop beim Beenden
                song_queues[message.guild.id] = []  # Leere die Warteschlange beim Beenden
                voice_clients[message.guild.id].stop()
                await voice_clients[message.guild.id].disconnect()
                del voice_clients[message.guild.id]
        except Exception as e:
            print(e)

    elif any(message.content.startswith(cmd) for cmd in commands["loop"]):
        try:
            args = message.content.split()
            if len(args) > 1 and args[1].lower() == "on":
                loop_status[message.guild.id] = True
                await message.channel.send("Loop aktiviert.")
            elif len(args) > 1 and args[1].lower() == "off":
                loop_status[message.guild.id] = False
                await message.channel.send("Loop deaktiviert.")
            else:
                await message.channel.send("Benutze `!loop on` zum Aktivieren oder `!loop off` zum Deaktivieren.")
        except Exception as e:
            print(e)



client.run(TOKEN)


