# iCal bot

A discord bot for keeping track of of your schedule, loading it directly from a URL to an iCal file.

## Prerequisites

+ Docker
+ A bot token on the Discord Developer Portal.

## How to run

Clone the repository to your machine.

Build the docker image:

```sh
docker build -t ical_bot .
```

Run the docker image

```sh
docker run -b \
  --env STORAGE_VOLUME=/store \
  --env DISCORD_TOKEN=YOUR-TOKEN-HERE \
  --mount source=icalvol,target=/store \
  ical_bot:latest
```

That's it!
