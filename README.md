# DC Music Bot

DC Music Bot is a Discord bot that allows users to search for, play, and manage music from YouTube directly within their Discord server. The bot supports various commands for music playback, playlist management, and more.

## Features

- Search for YouTube videos and play them in a voice channel.
- Create and manage playlists.
- Control music playback with commands like play, pause, resume, skip, and loop.
- Supports reconnecting and volume control with FFmpeg.

## Commands

### Search and Play Music

| Command          | Description                                      |
|------------------|--------------------------------------------------|
| `!suche [query]` | Search for a song on YouTube.                    |
| `!confirm`       | Confirm the suggested video and play it.         |
| `!play [url]`    | Play a specific YouTube video by URL.            |
| `!pause`         | Pause the current song.                          |
| `!resume`        | Resume the paused song.                          |
| `!skip`          | Skip the current song.                           |
| `!exit`          | Disconnect the bot from the voice channel.       |
| `!loop on`       | Enable loop mode.                                |
| `!loop off`      | Disable loop mode.                               |
| `!ping`          | Check if the bot is online.                      |

### Playlist Management

| Command              | Description                                      |
|----------------------|--------------------------------------------------|
| `!createplaylist [name]` | Create a new playlist.                       |
| `!addtoplaylist [name]`  | Add the last suggested song to the specified playlist. |
| `!viewplaylist [name]`   | View all songs in the specified playlist.    |
| `!playplaylist [name]`   | Play all songs in the specified playlist.    |

## Setup

1. Clone the repository.
2. Install the required dependencies:
    ```sh
    pip install discord.py yt-dlp youtubesearchpython
    ```
3. Replace the `TOKEN` variable in `dcmusic.py` with your Discord bot token.
4. Run the bot:
    ```sh
    python dcmusic.py
    ```

## Usage

Invite the bot to your Discord server and use the commands listed above to interact with it. The bot will join your voice channel and play music based on your commands.

## License

This project is licensed under the MIT License.

## Contributing

Feel free to open issues or submit pull requests for any improvements or bug fixes.

## Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [YouTube Search Python](https://github.com/alexmercerind/youtube-search-python)

---

For more details, refer to the source code in [dcmusic.py](http://_vscodecontentref_/1).