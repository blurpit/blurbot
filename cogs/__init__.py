import asyncio
import random
import sys
import traceback
from io import BytesIO

from discord import ApplicationContext as AppCtx, Option, Message, Member, VoiceChannel, ButtonStyle, Interaction, \
    VoiceClient, VoiceState, File, ActivityType, Activity, Status
from discord.commands import permissions, slash_command, SlashCommandGroup, message_command, user_command
from discord.ext.commands import Cog
from discord.ui import Button, View
from discord.utils import get

import garfield
import tictactoe
from youtube import TYDLSource, duration_string


def setup(bot):
    bot.add_cog(Admin(bot))
    bot.add_cog(Misc(bot))
    bot.add_cog(Garf(bot))
    bot.add_cog(TicTacToe(bot))
    bot.add_cog(Voice(bot))


class Admin(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name='ping')
    @permissions.is_owner()
    async def ping(self, ctx:AppCtx):
        """ Ping the bot. """
        await ctx.respond('Pong!')

    @slash_command(name='kill')
    @permissions.is_owner()
    async def kill(self, ctx:AppCtx):
        """ Kill the bot. """
        print('Killing...\n')
        await ctx.respond('Goodnight... 😴💤')
        await self.bot.close()

    cfg = SlashCommandGroup('cfg', 'get/set config')

    @cfg.command(name='get')
    @permissions.is_owner()
    async def cfg_get(
        self, ctx:AppCtx,
        key:Option(str, "Enter config key.")
    ):
        """ Get a configuration value. """
        val = self.bot.cfg[key]
        string = str(val)
        if len(string) > 1500:
            string = string[:1500] + '\n...'
        await ctx.respond('Key: `{}`\nType: `{}` ```{}```'.format(key, type(val), string))

    @cfg.command(name='set')
    @permissions.is_owner()
    async def cfg_set(
        self, ctx:AppCtx,
        key:Option(str, "Enter config key. Use append/remove/removei for list manipulation."),
        val:Option(str, "Enter value to set at the key.")
    ):
        """ Set a configuration value. """
        val = self.bot.cfg.infer_type(val)
        self.bot.cfg[key] = val
        self.bot.cfg.save()
        await ctx.respond('Key: `{}`\nType: `{}` ```{}```'.format(key, type(val), val))

    @cfg.command(name='reload')
    @permissions.is_owner()
    async def cfg_reload(self, ctx:AppCtx):
        """ Reload the configuration from the file. """
        self.bot.cfg.reload()
        await ctx.respond('Config reloaded from `{}`'.format(self.bot.cfg.fp))

    @slash_command(name='presence')
    @permissions.is_owner()
    async def presence(
        self, ctx:AppCtx,
        activity_type:Option(str, "Enter activity type", choices=["playing", "streaming", "listening", "watching", "competing", "online", "offline", "idle", "dnd"]),
        name:Option(str, "Enter presence text")
    ):
        """ Set the bot's presence. """
        if activity_type in ('online', 'offline', 'idle', "dnd"):
            await self.bot.change_presence(status=Status[activity_type])
        else:
            activity = Activity(type=ActivityType[activity_type], name=name)
            await self.bot.change_presence(activity=activity)
        await ctx.respond("Presence changed to **{}** '{}'".format(activity_type, name), ephemeral=True)


class Misc(Cog):
    def __init__(self, bot):
        self.bot = bot

    @message_command(name='OwOify')
    async def owo(self, ctx:AppCtx, msg:Message):
        """ Owoify a message by replacing R and L with W, and adding a random prefix & suffix. """
        if msg.author.bot:
            raise PermissionError("Cannot use message commands on bots.")

        substitution = {'r': 'w', 'l': 'w', 'R': 'W', 'L': 'W', 'no': 'nu', 'has': 'haz',
                        'have': 'haz', 'you': 'uu', ' the ': ' da ', 'The ': ' Da '}
        prefixes = ['<3', 'H-hewwo??', 'HIIII!', 'Haiiii!', 'Huohhhh.', 'OWO', 'OwO', 'UwU',
                    '88w88', 'H-h-hi']
        suffixes = [':3', 'UwU', 'ʕʘ‿ʘʔ', '>_>', '^_^', '.', 'Huoh.', '^-^', ';_;', 'xD',
                    'x3', ':D', ':P', ';3', 'XDDD', 'fwendo', 'ㅇㅅㅇ', '(人◕ω◕)', '（＾ｖ＾）',
                    'Sigh.', '._.', '>_<' 'xD xD xD', ':D :D :D']

        content = str(msg.clean_content)
        for key, replacement in substitution.items():
            content = content.replace(key, replacement)
        content = random.choice(prefixes) + ' ' + content + ' ' + random.choice(suffixes)

        await ctx.respond(content)

    @message_command(name='sPOnGeMoCK')
    async def spongemock(self, ctx:AppCtx, msg:Message):
        """ Spongemockify a message by randomly capitalizing its letters. """
        if msg.author.bot:
            raise PermissionError("Cannot use message commands on bots.")

        content = ''
        for letter in str(msg.clean_content):
            if random.random() > 0.5:
                content += letter.upper()
            else:
                content += letter.lower()
        await ctx.respond(content)

    @slash_command(name='roll')
    async def roll(
        self, ctx:AppCtx,
        rolls:Option(int, "Enter number of rolls to do", required=False, default=1),
        low:Option(int, "Enter lower bound", required=False, default=1),
        high:Option(int, "Enter upper bound", required=False, default=6)
    ):
        """ Roll random numbers. """
        if low > high:
            # Swap values if in wrong order
            low, high = high, low
        if not 1 <= rolls <= self.bot.cfg.misc.max_rolls:
            raise ValueError('Number of rolls must be between 1 and {}'.format(self.bot.cfg.misc.max_rolls))

        result = ', '.join(str(random.randint(low, high)) for _ in range(rolls))
        await ctx.respond('🎲 ' + result)

    @slash_command(name='choose')
    async def choose(
        self, ctx:AppCtx,
        choices:Option(str, description='List choices separated by commas')
    ):
        """ Choose a random option from a list of choices. """
        choice = random.choice(choices.split(',')).strip()
        await ctx.respond('I choose... **{}**!'.format(choice))


class Garf(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name='garf')
    async def garf(self, ctx:AppCtx):
        """ Fetch a random 3-panel Garfield comic. """
        await ctx.defer()
        comic = garfield.fetch(self.bot.cfg.garf.url)
        await ctx.respond(file=File(BytesIO(comic), filename='comic.gif'))

    # TODO: garfield scheduler


class TicTacToe(Cog):
    def __init__(self, bot):
        self.bot = bot

    @user_command(name='Play TicTacToe')
    async def tictactoe(self, ctx:AppCtx, user:Member):
        """ Start a game of TicTacToe. """
        await ctx.respond(
            "{}, it's your turn!".format(ctx.author.mention),
            view=tictactoe.TicTacToe(ctx.author, user, ai_game=user == self.bot.user)
        )


class Voice(Cog):
    def __init__(self, bot):
        self.bot = bot

    voice = SlashCommandGroup('voice', 'Play audio in a voice channel.')

    class StopButton(Button):
        def __init__(self, voice_client):
            self.vc = voice_client
            super().__init__(label='Stop', style=ButtonStyle.secondary, emoji='◽')

        async def callback(self, interaction:Interaction):
            if self.vc:
                await self.vc.disconnect()
            self.disabled = True
            self.label = 'Stopped'
            await interaction.response.edit_message(view=self.view)

    @voice.command(name='play')
    async def voice_play(
        self, ctx: AppCtx,
        query:Option(str, description='Enter a YouTube URL or search query.'),
        channel:Option(VoiceChannel, description='Voice channel', required=False)
    ):
        """ Play audio from a YouTube video in a voice channel. """
        await ctx.defer()

        await self.ensure_voice(ctx, channel)
        player = await TYDLSource.create(query, loop=self.bot.loop, stream=True)

        max_duration = self.bot.cfg.voice.max_video_duration
        if 0 < max_duration < player.duration_seconds:
            raise RuntimeError("Error: {}\nVideo exceeded maximum duration ({})."
                               .format(player.video_info, duration_string(max_duration)))

        def after(e):
            if e: traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            self.disconnect_voice(ctx, delay=self.bot.cfg.voice.disconnect_delay)

        vc:VoiceClient = ctx.voice_client
        vc.play(player, after=after)

        view = View(self.StopButton(vc))
        await ctx.respond('Playing: {}'.format(player.video_info), view=view)

    @voice.command(name='stop')
    async def voice_stop(self, ctx:AppCtx):
        """ Stop playing audio in a voice channel. """
        vc:VoiceClient = ctx.voice_client
        if vc:
            mention = vc.channel.mention
            await vc.disconnect()
            await ctx.respond('Disconnected from {}.'.format(mention))
        else:
            raise RuntimeError("Nothing is playing right now.")

    @Cog.listener()
    async def on_voice_state_update(self, member:Member, before:VoiceState, after:VoiceState):
        if before.channel != after.channel:
            vc:VoiceClient = get(self.bot.voice_clients, guild=member.guild)
            if vc is not None and all(m.bot for m in vc.channel.members):
                await vc.disconnect(force=False)

    @Cog.listener()
    async def on_application_command_error(self, ctx:AppCtx, exception):
        vc: VoiceClient = ctx.voice_client
        if vc:
            await vc.disconnect()

    async def ensure_voice(self, ctx:AppCtx, channel=None):
        """ Ensures that the bot is connected to a voice channel, or raises an error if no channel is given """
        if channel is not None:
            vc:VoiceClient = ctx.voice_client
            if self.bot.cfg.voice.force_connected and not (ctx.author.voice and ctx.author.voice.channel == channel):
                # User is not connected to the requested channel.
                raise RuntimeError("You aren't connected to {}.".format(channel.mention))
            if all(m.bot for m in channel.members):
                # Don't play to bots or to nobody
                raise RuntimeError("{} has no connected users.".format(channel.mention))
            if vc is None:
                # Not connected to a voice channel, connect
                await channel.connect()
            else:
                # Already connected to a voice channel, stop playing and move to it
                if vc.is_playing():
                    vc.stop()
                if vc.channel != channel:
                    await vc.move_to(channel)
        else:
            if ctx.author.voice:
                # No channel was given, connect to the author's voice channel
                await self.ensure_voice(ctx, channel=ctx.author.voice.channel)
            else:
                # No channel was given and the author is not connected to a voice channel, raise error
                raise RuntimeError("You aren't connected to a voice channel.")

    def disconnect_voice(self, ctx:AppCtx, delay=0):
        async def disconnect_task():
            vc:VoiceClient = ctx.voice_client
            if delay:
                await asyncio.sleep(delay)
            await vc.disconnect()

        self.bot.loop.create_task(disconnect_task())
