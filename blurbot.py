import asyncio
import random
import sys
import traceback
from io import BytesIO
from operator import attrgetter

import stopit as stopit
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import Bot, permissions, Message, File, Intents, Option, Embed, Color, Member, VoiceChannel, VoiceState, \
    ButtonStyle, Interaction
from discord.commands.context import ApplicationContext as AppCtx, AutocompleteContext as AutocompleteCtx
from discord.ui import Button, View
from discord.utils import get

import calc
import config
import garfield
from tictactoe import TicTacToe
from youtube import TYDLSource

config.load('data/config.json')
calc.load_custom_defined('data/saved_math.json')

intents = Intents.default()
intents.members = True
blurbot = Bot(intents=intents)
scheduler = AsyncIOScheduler()



# ----- Events ----- #

@blurbot.event
async def on_ready():
    print("\nLogged in as {}".format(blurbot.user))
    await blurbot.change_presence(activity=random.choice(config.presences))

    scheduler.remove_all_jobs()
    schedule_friday_garf()

@blurbot.event
async def on_application_command_error(ctx:AppCtx, exception):
    exception = exception.original
    await ctx.respond(str(exception))
    print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
    traceback.print_exception(
        type(exception), exception, exception.__traceback__, file=sys.stderr
    )

@blurbot.event
async def on_message(msg:Message):
    if msg.author == blurbot.user:
        return

    # Eggs
    if config.features['Eggs']:
        for reg, responses in config.eggs.items():
            if reg.fullmatch(msg.content):
                response = random.choice(responses)
                if callable(response):
                    response = response(msg)
                await msg.reply(response)

    # update presence every ~100 messages
    if random.random() < 1/100:
        await blurbot.change_presence(activity=random.choice(config.presences))

@blurbot.event
async def on_voice_state_update(member:Member, before:VoiceState, after:VoiceState):
    if before.channel != after.channel:
        voice_client = get(blurbot.voice_clients, guild=member.guild)
        if voice_client is not None and all(m.bot for m in voice_client.channel.members):
            await voice_client.disconnect(force=False)



# ----- Basic Commands ----- #

@blurbot.slash_command(name='ping', guild_ids=config.guilds)
@permissions.is_owner()
async def ping(ctx:AppCtx):
    """ Ping the bot. """
    await ctx.respond('Pong!')

@blurbot.slash_command(name='kill', guild_ids=config.guilds, default_permission=False)
@permissions.is_owner()
async def kill(ctx:AppCtx):
    """ Kill the bot. """
    print("Killing...\n")
    await ctx.respond("Goodnight... 😴💤")
    await blurbot.close()

@blurbot.slash_command(name='cfg', guild_ids=config.guilds, default_permission=False)
@permissions.is_owner()
async def cfg(
        ctx:AppCtx,
        option:Option(str, choices=list(config.features.keys())),
        value:Option(bool, required=False)
):
    """ Enable/disable features that may be annoying. """
    if value is not None:
        config.features[option] = value
        config.save('data/config.json')
    await ctx.respond('**{}**: {}.'.format(option, config.features[option]), ephemeral=True)

@blurbot.message_command(name='OwOify', guild_ids=config.guilds)
async def owo(ctx:AppCtx, msg:Message):
    """ Owoify a message by replacing R and L with W, and adding a random prefix & suffix. """
    if msg.author.bot:
        raise PermissionError("Cannot use message commands on bots.")

    substitution = {"r": "w", "l": "w", "R": "W", "L": "W", "no": "nu", "has": "haz", "have": "haz",
                    "you": "uu", " the ": " da ", "The ": " Da "}
    prefix = ["<3", "H-hewwo??", "HIIII!", "Haiiii!", "Huohhhh.", "OWO", "OwO", "UwU", "88w88", "H-h-hi"]
    suffix = [":3", "UwU", "ʕʘ‿ʘʔ", ">_>", "^_^", ".", "Huoh.", "^-^", ";_;", "xD", "x3", ":D", ":P", ";3",
              "XDDD", "fwendo", "ㅇㅅㅇ", "(人◕ω◕)", "（＾ｖ＾）", "Sigh.", "._.", ">_<" "xD xD xD", ":D :D :D"]

    content = msg.content
    for key, replacement in substitution.items():
        content = content.replace(key, replacement)
    content = random.choice(prefix) + ' ' + content + ' ' + random.choice(suffix)

    await ctx.respond(content)

@blurbot.message_command(name='sPOnGeMoCK', guild_ids=config.guilds)
async def spongemock(ctx:AppCtx, msg:Message):
    """ sPOnGeMoCK a mEsSAgE by randomizing its capitalization. """
    if msg.author.bot:
        raise PermissionError("Cannot use message commands on bots.")

    content = ''.join(map(lambda c: c.upper() if random.random() > 0.5 else c.lower(), msg.content))
    await ctx.respond(content)

@blurbot.slash_command(guild_ids=config.guilds)
async def garf(ctx:AppCtx):
    """ Fetches a randomized 3-panel Garfield comic. """
    await ctx.defer() # avoid timeout
    comic = garfield.fetch()
    await ctx.respond(file=File(BytesIO(comic), filename='comic.gif'))

@blurbot.slash_command(name='roll', guild_ids=config.guilds)
async def roll(
        ctx:AppCtx,
        rolls:Option(int, required=False, default=1),
        low:Option(int, required=False, default=1),
        high:Option(int, required=False, default=6)
):
    """ Roll a random number n times. """
    if low > high:
        # Swap values if in wrong order
        low, high = high, low
    if not 1 <= rolls <= 25:
        raise ValueError('Number of rolls must be between 1 and 25')

    result = ', '.join(str(random.randint(low, high)) for _ in range(rolls))
    await ctx.respond('🎲 ' + result)

@blurbot.slash_command(name='choose', guild_ids=config.guilds)
async def choose(ctx:AppCtx, choices:Option(str, description='List choices separated by commas')):
    """ Choose a random option from a list of choices. """
    choices = choices.split(',')
    await ctx.respond(f'I choose... **{random.choice(choices).strip()}**!')

@blurbot.user_command(name='Play TicTacToe', guild_ids=config.guilds)
async def tictactoe(ctx:AppCtx, user:Member):
    await ctx.respond(
        "{}, it's your turn!".format(ctx.author.mention),
        view=TicTacToe(ctx.author, user, ai_game=user == blurbot.user)
    )



# ----- Calc ----- #

# calculator = blurbot.command_group(
#     'calc', 'Evaluate math expressions, integrals, & derivatives.',
#     guild_ids=config.guilds
# )
#
# @calculator.command(name='eval', guild_ids=config.guilds)
# async def calc_eval(
#         ctx:AppCtx,
#         exp:Option(str, description='Expression to evaluate, ex. "2ln(1/5)".')
# ):
#     """ Evaluate an expression. """
#     with Timeout():
#         await ctx.defer()
#         exp = exp.replace(' ', '').replace(',', ', ')
#         answer = calc.PostfixEvaluator(calc.InfixToPostfix(exp).convert()).evaluate()
#         await ctx.respond(f'> {exp}\n= **{calc.format_value(answer)}**')
#
# def calc_function_autocomplete(option_name, builtin=True, custom=True, sort=False, func_filter=lambda f: True):
#     async def autocomplete(ctx:AutocompleteCtx):
#         criteria = lambda f: f.name.startswith(ctx.options[option_name]) and func_filter(f)
#         result = []
#         if custom:
#             result += list(map(attrgetter('name'), filter(criteria, calc.custom_functions.values())))
#         if builtin:
#             result += list(map(attrgetter('name'), filter(criteria, calc.functions.values())))
#         if sort:
#             result.sort()
#         return result
#     return autocomplete
#
# @calculator.command(name='define', guild_ids=config.guilds)
# async def calc_define(
#         ctx:AppCtx,
#         exp:Option(str, description='Expression to define a constant or function, '
#                                     'ex. "f(x, y) = x^2 + 2^sin(y)".')
# ):
#     """ Define a custom constant or function. """
#     with Timeout():
#         await ctx.defer()
#         exp = exp.replace(' ', '')
#         func = calc.define_custom(exp)
#         calc.save_custom_defined('data/saved_math.json')
#         await ctx.respond('Saved: ' + str(func))
#
# @calculator.command(name='undefine', guild_ids=config.guilds)
# async def calc_undefine(
#         ctx:AppCtx,
#         name:Option(str, autocomplete=calc_function_autocomplete('name', builtin=False))
# ):
#     """ Delete a defined constant or function. """
#     func = calc.remove_custom(name)
#     calc.save_custom_defined('data/saved_math.json')
#     await ctx.respond('Removed: ' + str(func))
#
# @calculator.command(name='get-defined', guild_ids=config.guilds)
# async def calc_get_defined(
#         ctx:AppCtx,
#         name:Option(str, description='Name of the constant/function. Leave blank to get all.',
#                     autocomplete=calc_function_autocomplete('name', builtin=False), required=False)
# ):
#     """ Get the definition for custom defined constants or functions. """
#     if name is None:
#         if not calc.custom_functions:
#             await ctx.respond('No custom constants or functions have been defined.', ephemeral=True)
#         else:
#             await ctx.respond(
#                 'Custom defined constants & functions:\n• ' + '\n• '.join(
#                     map(str, calc.custom_functions.values())
#                 ), ephemeral=True)
#     else:
#         func = calc.custom_functions.get(name)
#         if func is not None:
#             await ctx.respond(str(func), ephemeral=True)
#         else:
#             raise NameError('Custom function/constant does not exist: ' + name)
#
# @calculator.command(name='plot', guild_ids=config.guilds)
# async def calc_plot(
#         ctx:AppCtx,
#         func:Option(str, description='Use /calc define to create a function and enter its name here.',
#                     autocomplete=calc_function_autocomplete('func', func_filter=lambda f: len(f.args) == 1)),
#         xlow:Option(float, description='Lower bound for the x axis.'),
#         xhigh:Option(float, description='Upper bound for the x axis.'),
#         n:Option(int, description='Number of samples to take along the x axis.', default=1000, required=False)
# ):
#     """ Plot a one dimensional function on the xy plane. """
#     with Timeout():
#         await ctx.defer()
#         n = min(10000, max(1, n))
#         plot = calc.plot(func, xlow, xhigh, n)
#         await ctx.respond(file=File(plot, filename=func + '_plot.png'))
#
# @calculator.command(name='get-builtin', guild_ids=config.guilds)
# async def calc_get_builtin(ctx:AppCtx):
#     """ List built-in operators, constants, and functions. """
#     embed = Embed(color=Color.dark_red())
#     embed.set_author(name='/calc get-builtin')
#     embed.add_field(name='Operators', value="""
#         ` + ` Add
#         ` - ` Subtract
#         ` * ` Multiply
#         ` / ` Divide
#         ` % ` Modulo
#         ` ^ ` Exponent
#     """, inline=True)
#     embed.add_field(name='Constants', value="""
#         ` π ` or ` pi ` ~3.141592
#         ` e ` ~2.7182818
#         ` i ` Imaginary unit, i^2 = -1
#         ` inf ` Infinity
#     """, inline=True)
#     embed.add_field(name='Basic Functions', value="""
#         ` neg(x) ` Negation
#         ` abs(x) ` Absolute Value
#         ` rad(θ) ` Convert Degrees -> Radians
#         ` deg(θ) ` Convert Radians -> Degrees
#         ` round(x) ` Round to whole number (Banker's rounding)
#         ` floor(x) ` Floor (round down to whole number)
#         ` ceil(x) ` Ceiling (round up to whole number)
#     """, inline=False)
#     embed.add_field(name='Roots & Complex Functions', value="""
#         ` sqrt(x) ` Square Root
#         ` root(x, n) ` n-th Root
#         ` hypot(a, b) ` Pythagorean Theorem
#         ` real(c) ` Real component of a complex number
#         ` imag(c) ` Imaginary component of a complex number
#     """, inline=False)
#     embed.add_field(name='Trigonometric Functions', value="""
#         ` sin(θ) ` Sine
#         ` cos(θ) ` Cosine
#         ` tan(θ) ` Tangent
#         ` sec(θ) ` Secant
#         ` csc(θ) ` Cosecant
#         ` cot(θ) ` Cotangent
#         ` asin(x) ` Inverse Sine
#         ` acos(x) ` Inverse Cosine
#         ` atan(x) ` Inverse Tangent
#     """, inline=False)
#     embed.add_field(name='Hyperbolic Functions', value="""
#         ` sinh(x) ` Hyperbolic Sine
#         ` cosh(x) ` Hyperbolic Cosine
#         ` tanh(x) ` Hyperbolic Tangent
#     """, inline=False)
#     embed.add_field(name='Exponential & Logarithmic Functions', value="""
#         ` exp(x) ` Exponential Function, e^x
#         ` ln(x) ` Natural Logarithm (base e)
#         ` log(x) ` Logarithm (base 10)
#         ` logb(x, b) ` Logarithm (base b)
#     """, inline=False)
#     embed.add_field(name='Combinatorial & Random Functions', value="""
#         ` fact(n) ` Factorial
#         ` P(n, k) ` Permutations of k elements from a set of size n
#         ` C(n, k) ` Combinations of k elements from a set of size n
#         ` fib(n) ` Fibonacci Number
#         ` rand() ` Random real number between 0 and 1
#         ` randbetween(a, b) ` Random real number between a and b
#     """, inline=False)
#     embed.add_field(name='Calculus Functions', value="""
#         ` int(f, a, b) ` Definite integral of f(x)dx from a to b
#         ` deriv(f, x) ` Derivative of f(t)dt at (x, f(x))
#         ` nderiv(f, x, n) ` N-th derivative of f(t)dt at (x, f(x))
#     """)
#     embed.add_field(name='Coordinate System Conversion Functions', value="""
#         ` polar(x, y) ` 2D Cartesian -> Polar
#         ` rect(r, θ) ` 2D Polar -> Cartesian
#         ` crtcyl(x, y, z) ` 3D Cartesian -> Cylindrical
#         ` crtsph(x, y, z) ` 3D Cartesian -> Spherical
#         ` cylcrt(ρ, φ, z) ` 3D Cylindrical -> Cartesian
#         ` cylsph(ρ, φ, z) ` 3D Cylindrical -> Spherical
#         ` sphcrt(r, θ, φ) ` 3D Spherical -> Cartesian
#         ` sphcyl(r, θ, φ) ` 3D Spherical -> Cylindrical
#     """)
#     await ctx.respond(embed=embed, ephemeral=True)



# ----- Voice ----- #

voice = blurbot.command_group(
    'voice', 'Play audio in a voice channel.',
    guild_ids=config.guilds
)

@voice.command(name='play', guild_ids=config.guilds)
async def voice_play(
        ctx:AppCtx,
        query:Option(str, description='Enter a YouTube URL, or a YouTube search query.'),
        channel:Option(VoiceChannel, description='Voice channel', required=False)
):
    """ Play audio from a YouTube video in a voice channel. """
    await ctx.defer()

    await ensure_voice(ctx, channel)
    player = await TYDLSource.create(query, loop=blurbot.loop, stream=True)

    def after(e):
        if e: traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        schedule_disconnect_voice(ctx, delay=5, force=False)

    ctx.voice_client.play(player, after=after)

    stop_btn = Button(label='Stop', style=ButtonStyle.secondary, emoji='◽')
    view = View(stop_btn)
    async def stop(interaction:Interaction):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        stop_btn.disabled = True
        stop_btn.label = 'Stopped'
        await interaction.response.edit_message(view=view)
    stop_btn.callback = stop

    await ctx.respond('Playing: "**{}**" by {}. ({})'.format(player.title, player.uploader, player.duration), view=view)

@voice.command(name='stop', guild_ids=config.guilds)
async def voice_stop(ctx:AppCtx):
    """ Stop playing audio in a voice channel. """
    if ctx.voice_client:
        mention = ctx.voice_client.channel.mention
        await ctx.voice_client.disconnect()
        await ctx.respond('Disconnected from {}.'.format(mention))
    else:
        raise RuntimeError("Nothing is playing right now.")

async def ensure_voice(ctx:AppCtx, channel=None):
    """ Ensures that the bot is connected to a voice channel, or raises an error if no channel is given """
    if channel is not None:
        if all(m.bot for m in channel.members):
            # Don't play to bots or to nobody
            raise RuntimeError("That voice channel has no connected users.")
        if ctx.voice_client is None:
            # Not connected to a voice channel, connect
            await channel.connect()
        else:
            # Already connected to a voice channel, stop playing and move to it
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            if ctx.voice_client.channel != channel:
                await ctx.voice_client.move_to(channel)
    else:
        if ctx.author.voice:
            # No channel was given, connect to the author's voice channel
            await ensure_voice(ctx, channel=ctx.author.voice.channel)
        else:
            # No channel was given and the author is not connected to a voice channel, raise error
            raise RuntimeError("You aren't connected to a voice channel.")

def schedule_disconnect_voice(ctx:AppCtx, delay=0, force=True):
    async def disconnect():
        if delay:
            await asyncio.sleep(delay)
        if ctx.voice_client and (not ctx.voice_client.is_playing() or force):
            await ctx.voice_client.disconnect()
    blurbot.loop.create_task(disconnect())



# ----- Scheduled Tasks ----- #

def schedule_friday_garf():
    async def friday_garf():
        await blurbot.wait_until_ready()
        channel = blurbot.get_channel(913924123405729815) # blurbot testing grounds / main
        await channel.send(blurbot.get_emoji(920203046498209792)) # garfie baby

    scheduler.add_job(friday_garf, CronTrigger(
        day_of_week='fri', hour=0, minute=0, second=30,
        timezone='US/Eastern'
    ), id='task_friday_garf')
    scheduler.start()



# ----- Util ----- #

class Timeout(stopit.ThreadingTimeout):
    def __init__(self, seconds=20):
        super().__init__(seconds, swallow_exc=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        ret = super().__exit__(exc_type, exc_val, exc_tb)
        if self.state == self.TIMED_OUT:
            raise TimeoutError("Took too long to compute. (max {}s)".format(self.seconds))
        return ret



# ----- Main ----- #

if __name__ == '__main__':
    blurbot.run(config.load_token())
