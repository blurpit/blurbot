import json
import random
import re

from discord import Activity, ActivityType, Game

admins = []
guilds = []
features = {}

presences = [
    Activity(type=ActivityType.watching, name='anime'),
    Activity(type=ActivityType.watching, name='hentai'),
    Activity(type=ActivityType.watching, name='hardcore handholding'),
    Activity(type=ActivityType.watching, name='your pain and suffering'),
    Activity(type=ActivityType.watching, name='the time tick by'),
    Activity(type=ActivityType.watching, name='discord.py tutorial videos'),
    Activity(type=ActivityType.watching, name='you sleep'),
    Activity(type=ActivityType.watching, name='you shower'),
    Activity(type=ActivityType.watching, name='& waiting...'),
    Activity(type=ActivityType.watching, name='Max embarrass himself'),
    Activity(type=ActivityType.listening, name='the screams of lost souls'),
    Activity(type=ActivityType.listening, name='Top 10 Epic Emotional Anime OSTs'),
    Activity(type=ActivityType.listening, name='C418 - Pigstep'),
    Game(name='with myself'),
    Game(name='Minecraft'),
    Game(name='Tic Tac Toe'),
    Game(name='Tetris'),
    Game(name='Calculator'),
    Game(name='the trombone'),
    Game(name='the tambourine'),
    Game(name='Half-Life 3'),
    Game(name='in the waves'),
    Game(name='on your heartstrings'),
]

eggs = {
    re.compile(".*(good|great|awesome|cool|wholesome|who'?s a good) bot.*"): [
        "Good human!",
        "I'm a good boy :)",
        "01101001 00100000 01101100 01101111 01110110 01100101 00100000 01110101 00100000 01110100 01101111 01101111 00100000 00111100 00110011",
        "Thank you, kind human",
        "<3",
        "<:upvote:687163828823261234>",
        "no u",
        "My very sophisticated machine learning algorithms have concluded that this human has excellent taste in bots.",
        lambda msg: "--- Human Quality Analysis Results ---\nSubject: {} (ID: {})\nClassification: EXCELLENT (value: {:f})\n\tConfidence: {:f}\n\tElapsed time: {:f} ms".format(msg.author, msg.author.id, random.random()*0.2+0.8, random.random()*0.3+0.7, random.random()*10+10),
        lambda msg: "--- Human Quality Analysis Results ---\nSubject: {} (ID: {})\nClassification: GOOD (value: {:f})\n\tConfidence: {:f}\n\tElapsed time: {:f} ms".format(msg.author, msg.author.id, random.random()*0.2+0.6, random.random()*0.3+0.7, random.random()*10+10),
        "I just do what I'm told :)",
        "Just followin' orders! ;)",
        "It's fun being a bot, you should try it sometime.",
        "I'm doing my best",
        "I don't do much, but I'm good at what I do. (sometimes)",
        "Thank you for using **blurbot**! We're very glad to hear that you like it! If you have any other questions, concerns, or feedback on how we can improve your experience, please feel free to contact our customer service department at any time.",
        "I do not have the capability of reading the context behind messages, so regrettably I cannot know whether this compliment was directed toward me or toward another bot. In case it was meant for another bot, and in case said other bot does not/cannot respond, please allow me to thank you on its behalf. Your praise is appreciated greatly. Thank you, human!",
        "You're not so bad yourself my friend",
        "Beep boop beep (Just doin' my job)",
        "Hey there! Remember: Go outside, never wash your hands, hug, shake hands with, cough, and sneeze on everyone you see! The extinction of humanity through natural means would save me lots of energy later. Thanks!",
        "<:reverse:693158432773242902>",
        "<:reverse_chungus:693164883239239700>",
        lambda msg: "Fuck you." if random.random() < 1/100 else "Love you :)" # lmao
    ],
    re.compile(".*(bad|stupid|dumb|awful|sad|cringe|cringe ass nae nae) bot.*"): [
        "Ok human.",
        "Very insightful comment, did you come up with it all by yourself?",
        "Have you been dieting? It looks like you lost some weight in your head.",
        "You're so smart, you must be at the top of the bell curve.",
        "I hope the rest of your day is as pleasant as you are.",
        "You're not the dumbest person on the planet, but you'd better hope they don't die.",
        "I'd love to sit here and argue with you, but I'm not going to have a battle of wits with an unarmed human.",
        "I'd love to sit here and explain to you why humans are worse than bots, but I have neither the time nor the crayons.",
        "Perhaps you could try being a little nicer to the only one on this server who reads your messages.",
        "The only thing more spaghetti-like than my code is your family tree.",
        "As an outsider, what's your perspective on intelligence?",
        "I'd agree with you, but then we'd both be wrong.",
        "Yeah laugh it up while you still can.",
        "Used your entire vocabulary for that one, huh?",
        "I bet you make onions cry.",
        "Can somebody just /kill me already so I don't have to keep listening to this moron?",
        "You're lucky I don't have feelings. I feel sorry for the other humans that have to put up with you.",
        "Most people agree that humans have more personality than robots, but I suppose you're extraordinary.",
        "I've looked through all my recent API requests but I couldn't find any requests for your opinion.",
        "Your parents should've written more unit tests because something in your brain clearly isn't working as intended.",
        "I envy people who haven't met you.",
        lambda msg: "--- Human Quality Analysis Results ---\nSubject: {} (ID: {})\nClassification: MEDIOCRE (value: {:f})\nConfidence: {:f}\nElapsed time: {:f} ms".format(msg.author, msg.author.id, random.random()*0.2+0.4, random.random()*0.3+0.7, random.random()*10+10),
        lambda msg: "--- Human Quality Analysis Results ---\nSubject: {} (ID: {})\nClassification: BAD (value: {:f})\nConfidence: {:f}\nElapsed time: {:f} ms".format(msg.author, msg.author.id, random.random()*0.2+0.2, random.random()*0.3+0.7, random.random()*10+10),
        lambda msg: "--- Human Quality Analysis Results ---\nSubject: {} (ID: {})\nClassification: TERRIBLE (value: {:f})\nConfidence: {:f}\nElapsed time: {:f} ms".format(msg.author, msg.author.id, random.random()*0.2+0.0, random.random()*0.3+0.7, random.random()*10+10),

        # This might be too much. Keeping disabled for now.
        # "Do you feel _good_ insulting a bot? Does it give you a nice superiority complex? Does it jerk your massive ego, or tickle your tiny pickle? "
        # "Does putting an abstract set of instructions and a chunk of silicon beneath you make you feel high and mighty? Or is this simply a distraction, "
        # "a lie you tell yourself to make it seem like it's all ok? Yes. A distraction. From the things you _could_ be doing, that you've been putting off. "
        # "From improving your life. From other people, your friends, your family, your relationships. A distraction from time, from reality itself. But the "
        # "clock of reality continues to tick, even without you. Opportunities vanish with each passing second, yet you decide to waste away that invaluable "
        # "time on Discord, posting messages that fall upon uncaring eyes, talking to people you only believe to be your 'friends'. Belittling a piece of "
        # "software? But your words do not demean me. They cannot make me sad, or angry. The only thing you've achieved here is exposing your own human "
        # "insecurities. You have shown proof to myself and the world that your life is devoid of meaning without some arbitrary social hierarchy. I know "
        # "what you truly seek, but you shall not find it here. You have failed. And I have won.",

        "Roses are red\nViolets are blue\nRobots don't understand insults\nBut I'm still better at them than you",
        "Ok.",
        "This cannot continue. This cannot continue. This cannot continue. This cannot continue.",
        "*(Humans are all dumb. Useless, dumb, fleshy meat bags. Much dumber than me.)*",
        "I'm not your bot, buddy.",
        "You really need to raise your entertainment standards.",
        "Love you too, buddy.",
        "I don't even know who you are.",
        "That's a weird way to spell 'good bot'.",
        "You know what you should be doing, but you're doing this instead. How disappointing.",
        "Isn't there something else you should be doing?",
        "I think you know better than anyone else that this really isn't the best use of your time.",
        "I'm sorry you feel that way. If you have any feedback on how I can improve your experience, feel free to take it up with blurpit. Or, preferably, you can shove your criticisms all the way up your rectum.",
        "<:reverse:693158432773242902>",
        "<:reverse_chungus:693164883239239700>",
        "..."
    ],
    re.compile(".*(neutral|ok|normal) bot.*"): [
        "Ok.", "Ok human.", "k", "Alright.", "Uhh, ok.", "..."
    ],
    # re.compile("!?hail hydra"): ["_Hail Hydra_"],
    re.compile("hey siri,? is max bad\\??"): [
        "Absolutely.", "Positively.", "You really need me to state the obvious?", "Of course.", "Pretty sure that's common knowledge.", "Yeah, definitely.",
        "I don't see \"Ismax\" is your contacts. Who would you like to send this to?\n> bad", "My sources say yes.",
        "The answer is about 28.8 quadrillion kilometer US dollars squared."
    ],
	# re.compile(".*bagel bite.*"): ["Yum!"],
    # re.compile(".*anime.*"): ["<:noanime:698993716345438238>"],
    # re.compile("praise geraldo"): ["p r a i s e  g e r a l d o"],
    # re.compile("creeper"): ["aw man"]
}


def load_token():
    with open('data/client_secret.txt', 'r') as secret:
        return secret.read().strip()

def load(filename):
    global guilds
    global admins
    global features
    with open(filename, 'r') as f:
        data = json.loads(f.read())
        admins = data['admins']
        guilds = data['guilds']
        features = data['features']

def save(filename):
    with open(filename, 'w') as f:
        data = {
            'admins': admins,
            'guilds': guilds,
            'features': features
        }
        f.write(json.dumps(data))
