from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
from typing import Optional, Union

import discord
import discord.ext.commands as discord_cmds
import discord.ext.tasks as discord_tasks
from discord import embeds
from icalevents.icalevents import events

from channel_url_db import ChannelUrlDb, ICalRecord, ICalRole
from ical_events import day_with_offset, get_day_events, CET_TZ

intents = discord.Intents.default()
intents.typing = False
intents.presences = False


logger = logging.getLogger("ical_bot")
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler("ical_bot.log")
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


async def wait_until(dt: datetime.datetime):
    # sleep until the specified datetime
    now = datetime.datetime.now(tz=CET_TZ)

    logger.debug(f"Waiting for {(dt - now)} until {dt} ...")
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
            logger.info(
                f"Skipping updates because tomorrow ({tomorrow}) is the weekend!"
            )

        for channel_id in self.bot.url_db.channels:
            # Start by finding the discord channel object from it's ID
            channel = discord.utils.get(self.bot.get_all_channels(), id=channel_id)
            if channel is None:
                logger.error(f"Couldn't find channel {channel_id}")

            # Then load the events from the exclusion calendars
            skip_channel = False
            for record in list(
                self.bot.url_db.get_records_by_channel(
                    channel_id=channel_id, role=ICalRole.exclusion_list
                )
            ):
                for e in get_day_events(record.url, tomorrow):
                    skip_channel |= e.contains_day(tomorrow)

            if skip_channel:
                logger.info(
                    f"Excluding channel {channel_id} due to event in exclusion calendar"
                )
                continue

            # Load all events from calendars
            events: list[ICalRecord] = []
            for record in self.bot.url_db.get_records_by_channel(
                channel_id=channel_id, role=ICalRole.event_source
            ):
                events.extend(get_day_events(record.url, tomorrow))

            if len(events) > 0:
                # Build and send an embed from the list of events
                embed = self.bot.construct_embed(events, tomorrow)
                logger.info(f"Sending updated info to channel {channel_id}")
                await channel.send(embed=embed)

    @update_ical.before_loop
    async def before_update_ical(self):
        update_time = datetime.time(hour=20, minute=0, second=0, microsecond=0)
        now = datetime.datetime.now(tz=CET_TZ)
        desired_time = now + datetime.timedelta(
            hours=(update_time.hour - now.hour) % 24 - 1,
            minutes=(update_time.minute - now.minute) % 60 - 1,
            seconds=(update_time.second - now.second) % 60 - 1,
            microseconds=(update_time.microsecond - now.microsecond) % 1e6,
        )
        await self.bot.wait_until_ready()
        await wait_until(desired_time)
        logger.debug("Starting update loop")


class AdeBot(discord_cmds.Bot):
    def __init__(self, prefix: str, db_file: Path = Path("records.pickle")):
        super().__init__(prefix)
        self.url_db = ChannelUrlDb(db_file)

    async def on_ready(self):
        logger.info("Logged on as {0}!".format(self.user))

    def construct_embed(
        self,
        events: list[ICalRecord],
        day: datetime.date,
    ):
        embedVar = discord.Embed(
            title=f"Agenda for {day.strftime(f'%A %d/%m/%Y')}", color=0x00FF00
        )

        event_count = 0

        for e in events:
            embedVar.add_field(
                name=e.summary,
                value=(
                    f"{e.start.strftime(f'%H:%M')} - {e.end.strftime(f'%H:%M')}\n"
                    f"{e.location}"
                ),
                inline=False,
            )
            event_count += 1

        if event_count == 0:
            embedVar.add_field(
                name="Nothing to do!",
                value="Have a beer 🍻",
                inline=False,
            )

        return embedVar


if __name__ == "__main__":
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN environment variable was not set")
        exit(1)
    
    STORAGE_VOLUME = os.getenv("STORAGE_VOLUME")
    if not STORAGE_VOLUME:
        logger.critical("STORAGE_VOLUME environment variable was not set")
        exit(1)
    
    DISCORD_TOKEN = DISCORD_TOKEN
    STORAGE_VOLUME = Path(STORAGE_VOLUME)

    bot = AdeBot("!", STORAGE_VOLUME / "records.pickle" )
    cog = AdeGetterCog(bot)
    bot.add_cog(cog)

    @bot.command()
    async def info(ctx):
        """Returns the list of calenders registed for the current Discord channel"""

        embedVar = discord.Embed(
            title=f"Calendars registed in this channel", color=0x0000FF
        )

        nb_channels = 0
        for rec in sorted(
            bot.url_db.get_records_by_channel(ctx.channel.id), key=lambda x: x.role.name
        ):
            embedVar.add_field(
                name=rec.role.name,
                value=rec.url,
                inline=False,
            )
            nb_channels += 1

        if nb_channels == 0:
            embedVar.add_field(
                name="No channels registed yet.",
                value="Use `!register_url` to register a new calendar",
                inline=False,
            )

        await ctx.send(embed=embedVar)

    @bot.command()
    async def register_url(ctx, url: str, role: Optional[str]):
        """Registers an iCal calendar url to use in the current channel
        Args:
            - url: the url to a publically accessible iCal file
            - role [event_source | exclusion_list]
                Either use the calendar to find events, or use it as a day
                exclusion list (holidays for example)
        """

        record = ICalRecord(
            channel_id=ctx.channel.id, url=url, role=ICalRole.from_string(role)
        )

        if record.role is None:
            logger.error(f"Unknown role {role}")
            await ctx.send(f"Unknown role {role}")

        logger.info(f"Mapping channel {ctx.channel} to url {url}")
        bot.url_db.add_record(record)
        await ctx.send(
            f"Saved url {record.url} with the role {record.role.name} for the current channel!"
        )

    @bot.command()
    async def delete_url(ctx, url: str, role: Optional[str]):
        """Removes an iCal calendar url from the current channel"""

        msg_lines: list[str] = []

        for rec in bot.url_db.get_records_by_channel(ctx.channel.id):
            if rec.url == url and (role is None or rec.role == role):
                logger.info(f"Removing calendar {rec.url} from channel {ctx.channel}")
                bot.url_db.remove_record(rec)
                msg_lines.append(
                    f"Removed calendar {rec.url} from channel {ctx.channel}"
                )

        await ctx.send("\n".join(msg_lines))

    @bot.command()
    async def get(ctx, day: Union[str, int, None] = 0):
        """Show a day's events"""

        logger.info(f"Events requested in channel {ctx.channel} for day {day}")

        if day == "today" or day is None:
            day = day_with_offset()
        elif day == "tomorrow":
            day = day_with_offset(offset=1)
        else:
            try:
                day = day_with_offset(offset=int(day))
            except ValueError:
                msg = (
                    f"Couldn't parse {day} as a day offset!\n"
                    "Accepted values: 'today', 'tomorrow', integers"
                )
                logger.error(msg)
                await ctx.send(msg)

        if ctx.channel.id not in bot.url_db.channels:
            await ctx.send(
                "No iCal url registered for current channel!\n"
                "Register one now by sending `!register_url url_to_ical_calendar`"
            )
            return

        # Load all events from calendars
        events: list[ICalRecord] = []
        for record in bot.url_db.get_records_by_channel(
            channel_id=ctx.channel.id, role=ICalRole.event_source
        ):
            events.extend(get_day_events(record.url, day))

        # Build and send an embed from the list of events
        embed = bot.construct_embed(events, day)
        logger.info(f"Sending updated info to channel {ctx.channel.id}")
        await ctx.channel.send(embed=embed)

    bot.run(DISCORD_TOKEN)
