# r4n

A [Discord](https://discord.com/) interface for the [eurocore](https://github.com/europeia/eurocore) API. Named in honor of the illustrious [r3n](https://forums.europeians.com/index.php?members/r3naissanc3r.249319/) by [SkyGreen](https://forums.europeians.com/index.php?members/skygreen.6014608/)

### Commands

Up to date documentation can be found on the [Europeian forum](https://forums.europeians.com/index.php?threads/etc-r4n-discord-bot-user-guide.10069056/).

### Configuration:

- `DISCORD_TOKEN`: Discord bot token [required]
- `EUROCORE_URL`: eurocore URL [required]
- `HOST_USER`: bot host [required]
- `LOG_LEVEL`: log level [DEBUG, INFO, WARN, ERROR], default: INFO

### Run:

#### uv

```sh
HOST_USER=your_host DISCORD_TOKEN=your_token EUROCORE_URL=http://eurocore uv run main.py
```

#### Docker

```sh
docker run -e DISCORD_TOKEN=your_token -e EUROCORE_URL=http://eurocore -e USER=your_host ghcr.io/europeia/r4n:latest
```
