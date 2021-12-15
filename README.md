# iCal bot

A discord bot for keeping track of of your schedule, loading it directly from a URL to an iCal file.

## Prerequisites

Install the following:

- A recent version of Python (3.10 preferred, 3.7 probably works but isn't tested)
- The following modules (available in pip):
  - discord.py
  - icalevents
- This module, duh...

Then create an **auth.json** file in the root of your working directory following this template:

```json
{
  "TOKEN": "your_bot_token_here"
}
```

You will obtain this bot token on the Discord Developer Portal after creating your application and bot.

## How to run

```sh
$ python ical_bot/bot.py
```

That's it!
