import asyncio
import os
import random
import sys
import traceback
from io import BytesIO

import calc
import requests
import stopit
from discord import ApplicationContext as AppCtx, Message, Member, VoiceChannel, ButtonStyle, Interaction, \
    VoiceClient, VoiceState, File, ActivityType, Activity, Status, default_permissions, Permissions, option
from discord.commands import slash_command, SlashCommandGroup, message_command, user_command
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
    bot.add_cog(UrbanDictionary(bot))
    bot.add_cog(TicTacToe(bot))
    bot.add_cog(Voice(bot))
    bot.add_cog(Calculator(bot))


class Admin(Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx:AppCtx):
        if ctx.author.id not in self.bot.owner_ids:
            raise PermissionError('This command is only available to blurbot admins.')

    @slash_command(name='ping')
    @default_permissions(administrator=True)
    async def ping(self, ctx:AppCtx):
        """ Ping the bot. """
        await ctx.respond('Pong!')

    @slash_command(name='kill')
    @default_permissions(administrator=True)
    async def kill(self, ctx:AppCtx):
        """ Kill the bot. """
        print('Killing...\n')
        await ctx.respond('Goodnight... 😴💤')
        await self.bot.close()

    cfg = SlashCommandGroup(
        'cfg',
        'get/set config',
        default_member_permissions=Permissions(administrator=True)
    )

    @cfg.command(name='get')
    @option('key', str, description='Enter config key')
    async def cfg_get(self, ctx:AppCtx, key):
        """ Get a configuration value. """
        val = self.bot.cfg[key]
        string = str(val)
        if len(string) > 1500:
            string = string[:1500] + '\n...'
        await ctx.respond('Key: `{}`\nType: `{}` ```{}```'.format(key, type(val), string))

    @cfg.command(name='set')
    @option('key', str, description='Enter config key. Use append/remove/removei for list manipulation.')
    @option('val', str, description='Enter value to set at the key')
    async def cfg_set(self, ctx:AppCtx, key, val):
        """ Set a configuration value. """
        val = self.bot.cfg.infer_type(val)
        self.bot.cfg[key] = val
        self.bot.cfg.save('BLURBOT_CONFIG')
        await ctx.respond('Key: `{}`\nType: `{}` ```{}```'.format(key, type(val), val))

    @cfg.command(name='reload')
    async def cfg_reload(self, ctx:AppCtx):
        """ Reload the configuration from the file. """
        self.bot.cfg.reload('BLURBOT_CONFIG')
        await ctx.respond('Config reloaded from `{}`'.format(self.bot.cfg.fp))

    @slash_command(name='presence')
    @default_permissions(administrator=True)
    @option(
        'activity_type', str,
        description='Enter activity type',
        choices=['playing', 'streaming', 'listening', 'watching', 'competing',
                 'online', 'offline', 'idle', 'dnd']
    )
    @option('name', str, description='Enter presence text')
    async def presence(self, ctx:AppCtx, activity_type, name):
        """ Set the bot's presence. """
        if activity_type in ('online', 'offline', 'idle', 'dnd'):
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
            raise PermissionError('Cannot use message commands on bots.')

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
            raise PermissionError('Cannot use message commands on bots.')

        content = ''
        for letter in str(msg.clean_content):
            if random.random() > 0.5:
                content += letter.upper()
            else:
                content += letter.lower()
        await ctx.respond(content)

    @slash_command(name='roll')
    @option('rolls', int, description='Enter number of rolls to do', required=False, default=1)
    @option('low', int, description='Enter lower bound', required=False, default=1)
    @option('high', int, description='Enter upper bound', required=False, default=6)
    async def roll(self, ctx:AppCtx, rolls, low, high):
        """ Roll random numbers. """
        if low > high:
            # Swap values if in wrong order
            low, high = high, low
        if not 1 <= rolls <= self.bot.cfg.misc.max_rolls:
            raise ValueError('Number of rolls must be between 1 and {}'.format(self.bot.cfg.misc.max_rolls))

        result = ', '.join(str(random.randint(low, high)) for _ in range(rolls))
        await ctx.respond('🎲 ' + result)

    @slash_command(name='choose')
    @option('choices', str, description='List choices separated by commas')
    async def choose(self, ctx:AppCtx, choices):
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


class UrbanDictionary(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name='ud')
    @option('term', str, description='Enter term to define')
    async def ud(self, ctx:AppCtx, term):
        """ Command totally not shamelessly stolen from deadbeef. """
        data = requests.get('https://api.urbandictionary.com/v0/define?term={}'.format(term)).json()['list']
        if not data:
            await ctx.respond("**{}**\nThere are no definitions for this word.".format(term))
            return

        term = data[0]['word'].strip()
        definition = data[0]['definition'].strip().replace('[', '').replace(']', '')
        example = data[0]['example'].strip(' []').replace('[', '').replace(']', '')
        response = "**{}**\n{}".format(term, definition)
        if example:
            response += '\n\n*{}*'.format(example)
        await ctx.respond(response)


class TicTacToe(Cog):
    def __init__(self, bot):
        self.bot = bot

    @user_command(name='Play TicTacToe')
    async def tictactoe(self, ctx:AppCtx, user:Member):
        """ Start a game of TicTacToe. """
        if user.bot:
            raise ValueError("Tic tac toe AI is broken right now. :/")
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
    @option('query', str, description='Enter a YouTube URL or search query')
    @option('channel', VoiceChannel, description='Voice channel', required=False)
    async def voice_play(self, ctx: AppCtx, query, channel):
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


class Calculator(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.math_ctx = calc.create_default_context()
        self.load()

    class TimeoutError(Exception):
        pass

    def load(self):
        calc.load_contexts(self.math_ctx, os.environ['BLURBOT_SAVED_MATH'])
    def save(self):
        os.environ['BLURBOT_SAVED_MATH'] = calc.save_contexts(self.math_ctx)

    group = SlashCommandGroup('calc', 'Play audio in a voice channel.')

    @group.command(name='eval')
    @option('expression', str, description='Enter an expression to evaluate')
    async def evaluate(self, ctx:AppCtx, expression):
        """ Evaluate an expression. """
        await ctx.defer()
        with stopit.ThreadingTimeout(self.bot.cfg.calc.timeout) as timer:
            expression = expression.replace(' ', '')
            result = calc.evaluate(self.math_ctx, expression)
            if isinstance(result, calc.CustomFunction):
                self.math_ctx.add(result)
                self.save()

        if timer.state == timer.TIMED_OUT:
            raise self.TimeoutError("Evaluation took too long.")

        await ctx.respond("> `{}`\n```{}```".format(expression, result))

    @group.command(name='latex')
    @option('expression', str, description='Enter an expression, or LaTeX starting and ending with $')
    @option('evaluate', bool, description='If true, the expression will be evaluated first before being converted to LaTeX', required=False, default=False)
    @option('render', bool, description='If true, render the expression as an image, otherwise print the text', required=False, default=True)
    async def latex(self, ctx:AppCtx, expression, evaluate, render):
        """ Render an expression as a LaTeX image. """
        await ctx.defer()
        with stopit.ThreadingTimeout(self.bot.cfg.calc.timeout) as timer:
            if expression.startswith('$') and expression.endswith('$'):
                tex = expression.lstrip('$').rstrip('$')
            else:
                if evaluate:
                    expression = calc.evaluate(self.math_ctx, expression)
                tex = calc.latex(self.math_ctx, expression)
            if render:
                img = calc.latex_to_image(tex, dpi=self.bot.cfg.calc.latex_dpi)

        if timer.state == timer.TIMED_OUT:
            raise self.TimeoutError("Evaluation took too long.")

        if render:
            with BytesIO() as bio:
                img.save(bio, format='png')
                bio.seek(0)
                await ctx.respond(file=File(bio, 'tex.png'))
        else:
            await ctx.respond('```' + tex + '```')

    @group.command(name='graph')
    @option('expression', str, description='Enter an expression to graph, or a function name')
    @option('xlow', float, description='Enter lower x axis bound', required=False, default=-10)
    @option('xhigh', float, description='Enter upper x axis bound', required=False, default=10)
    @option('ylow', float, description='Enter lower y axis bound', required=False, default=None)
    @option('yhigh', float, description='Enter upper y axis bound', required=False, default=None)
    async def graph(self, ctx: AppCtx, expression, xlow, xhigh, ylow, yhigh):
        """ Plot a 1-dimensional function on the xy plane. """
        await ctx.defer()

        trimmed = expression.replace(' ', '').lower()
        if trimmed in self.bot.cfg.calc.meme_graphs:
            await ctx.respond(self.bot.cfg.calc.meme_graphs[trimmed])
            return

        with stopit.ThreadingTimeout(self.bot.cfg.calc.timeout) as timer:
            fig = calc.graph(
                self.math_ctx, expression,
                xlow, xhigh,
                ylow, yhigh,
                tex_title=self.bot.cfg.calc.use_tex_graph_title
            )
            bio = calc.savefig_bytesio(fig)

        if timer.state == timer.TIMED_OUT:
            raise self.TimeoutError("Evaluation took too long.")

        await ctx.respond(file=File(bio, 'graph.png'))
