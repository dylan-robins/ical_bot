from __future__ import annotations

import asyncio
import datetime
import json
from pathlib import Path
from typing import Union

import discord
import discord.ext.commands as discord_cmds
import discord.ext.tasks as discord_tasks

from channel_url_db import ChannelUrlDb
from ical_events import day_with_offset, get_day_events

intents = discord.Intents.default()
intents.typing = False
intents.presences = False


async def wait_until(dt: datetime.datetime):
    # sleep until the specified datetime
    now = datetime.datetime.now()

    print(f"Waiting for {(dt - now)} until {dt} ...")
    await asyncio.sleep((dt - now).total_seconds())


class AdeGetterCog(discord_cmds.Cog):
    def __init__(self, bot: AdeBot):
        self.index = 0
        self.bot = bot
        self.update_ical.start()

    def cog_unload(self):
        self.update_ical.cancel()

    @discord_tasks.loop(hours=24)
    async def update_ical(self):
        tomorrow = day_with_offset(offset=1)
        if tomorrow.weekday() > 5:
            print(f"Skipping updates because tomorrow ({tomorrow}) is the weekend!")
        for channel_id, url in self.bot.urls_by_channel.items:
            print(f"Looking for channel {channel_id} in")
            for ch in self.bot.get_all_channels():
                print(f"  - {ch}")
            channel = discord.utils.get(self.bot.get_all_channels(), id=channel_id)

            embed = self.bot.construct_embed(url, tomorrow)
            print(f"Sending updated info to channel {channel_id}")
            await channel.send(embed=embed)

    @update_ical.before_loop
    async def before_update_ical(self):
        update_time = datetime.time(hour=20, minute=0, second=0, microsecond=0)
        now = datetime.datetime.now()
        desired_time = now + datetime.timedelta(
            hours=(update_time.hour - now.hour) % 24 - 1,
            minutes=(update_time.minute - now.minute) % 60 - 1,
            seconds=(update_time.second - now.second) % 60 - 1,
            microseconds=(update_time.microsecond - now.microsecond) % 1e6,
        )
        await self.bot.wait_until_ready()
        await wait_until(desired_time)
        print("Starting update loop")


class AdeBot(discord_cmds.Bot):
    def __init__(self, prefix: str, db_file: Path = Path("records.pickle")):
        super().__init__(prefix)
        self.urls_by_channel = ChannelUrlDb(db_file)

    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    def construct_embed(self, url: str, day: datetime.date):
        print(f"Updating calendar (url = {url})")

        embedVar = discord.Embed(
            title=f"Agenda for {day.strftime(f'%A %d/%m/%Y')}", color=0x00FF00
        )

        for e in get_day_events(url, day=day):
            embedVar.add_field(
                name=e.summary,
                value=(
                    f"{e.start.strftime(f'%H:%M')} - {e.end.strftime(f'%H:%M')}\n"
                    f"{e.location}"
                ),
                inline=False,
            )

        return embedVar


if __name__ == "__main__":
    authfile = Path("auth.json")
    if not authfile.is_file():
        print("Error: couldn't open auth.json file.")
    auth = json.loads(authfile.read_text())

    bot = AdeBot("!")
    cog = AdeGetterCog(bot)
    bot.add_cog(cog)

    @bot.command()
    async def register_url(ctx, url: str):
        """Sets the iCal calendar url to use in the current channel"""

        print(f"Mapping channel {ctx.channel} to url {url}")
        bot.urls_by_channel.set_record(ctx.channel.id, str(url))
        await ctx.send(f"Saved url {url} for the current channel!")

    @bot.command()
    async def get(ctx, day: Union[str, int, None] = 0):
        """Show a day's events"""

        print(f"Events requested in channel {ctx.channel} for day {day}")

        if day == "today" or day is None:
            day = day_with_offset()
        elif day == "tomorrow":
            day = day_with_offset(offset=1)
        else:
            try:
                day = day_with_offset(offset=int(day))
            except ValueError:
                msg = (
                    f"Error, couldn't parse {day} as a day offset!\n"
                    "Accepted values: 'today', 'tomorrow', integers"
                )
                print(msg)
                await ctx.send(msg)

        if ctx.channel.id not in bot.urls_by_channel.channels:
            await ctx.send(
                "No iCal url registered for current channel!\n"
                "Register one now by sending `!register_url url_to_ical_calendar`"
            )
            return

        url_to_update = bot.urls_by_channel.get_record(ctx.channel.id)
        await ctx.send(embed=bot.construct_embed(url_to_update, day_with_offset(day)))

    bot.run(auth["TOKEN"])
