import os
import random
import re
import sys
import traceback

from discord import ApplicationContext as AppCtx, Message
from discord import Intents
from discord.ext.commands import Bot

import cogs
from util import Config, render_egg, get_presence


class Blurbot(Bot):
    def __init__(self):
        self.cfg = Config()
        self.cfg.reload('BLURBOT_CONFIG')
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            intents=intents,
            owner_ids=self.cfg.admins,
            debug_guilds=self.cfg.guilds
        )
        cogs.setup(self)

    async def on_ready(self):
        print("\nLogged in as {}".format(self.user))
        if self.cfg.presences.enabled:
            activity = get_presence(random.choice(self.cfg.presences.data))
            await blurbot.change_presence(activity=activity)

    async def on_message(self, msg:Message):
        if msg.author.bot:
            return

        # Chance presences
        if self.cfg.presences.enabled and random.random() < self.cfg.presences.change_chance:
            activity = get_presence(random.choice(self.cfg.presences.data))
            await blurbot.change_presence(activity=activity)

        # Eggs
        if self.cfg.eggs.enabled:
            for egg in self.cfg.eggs.data:
                if re.fullmatch(egg.regex, msg.content):
                    await msg.reply(render_egg(random.choice(egg.responses), msg), mention_author=False)
                    break

        # Reactions
        if self.cfg.reactions.enabled:
            for reac in self.cfg.reactions.data:
                if reac.enabled and random.random() < reac.chance and (reac.users == 'all' or msg.author.id in reac.users):
                    response = random.choice(reac.responses)
                    if reac.action == 'reply':
                        await msg.reply(response, mention_author=False)
                    elif reac.action == 'react':
                        await msg.add_reaction(response)
                    break

    async def on_application_command_error(self, ctx:AppCtx, exception):
        exception = getattr(exception, 'original', exception)

        text = str(exception)
        if len(text) > 2000:
            text = text[:1997] + '...'
        await ctx.respond(text, ephemeral=True)
        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        traceback.print_exception(type(exception), exception,
                                  exception.__traceback__, file=sys.stderr)


if __name__ == '__main__':
    blurbot = Blurbot()
    blurbot.run(os.environ['BLURBOT_SECRET'])
