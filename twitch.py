import string, random, csv, os, json, time, traceback, threading, uuid, re, wikipedia, aiohttp, requests, dice
from xml.dom import minidom
from os import path
from datetime import datetime
from twitchio.ext import commands
from twitchio.ext.commands.errors import CommandNotFound
from config import *
from lists import *
from models import *

aio_session = aiohttp.ClientSession()
creator_db_id= int(os.environ.get('creator_id', '696969'))
channel_name = os.environ.get('twitch_username', 'USERNAMEFAIL')

#terminal color output.
class Color:
    blue = '\u001b[34;1m'
    yellow = '\u001b[33m'
    white = '\u001b[37m'


bot = commands.Bot(
    irc_token = password,
    client_id = 'test',
    nick = nick,
    prefix = '!',
    initial_channels = [channel_name]
)

#start actual bot stuff.
def log_message(username, message):
    now = datetime.now()
    stamp = now.strftime("%m/%d/%Y %H:%M:%S")
    log = TwitchLog(event_time = stamp, username = username, message = message, creator_id = creator_db_id)
    session.add(log)
    session.commit()

def get_commands_list():
    commands_list =[]
    commands_entries = session.query(Command).filter_by(channel_id = creator_db_id).all()
    for command in commands_entries:
        commands_list.append(command.keyword)

    return commands_list

def insert_response(command_id, response):
    new_response = Response(command_id = command_id, output=response)
    session.add(new_response)
    session.commit()

def insert_command(keyword, response):
    new_command = Command(keyword = keyword, channel_id = creator_db_id)
    session.add(new_command)
    session.commit()
    insert_response(new_command.id, response)

def get_command_id(keyword):
    command = session.query(Command).filter_by(keyword = keyword, channel_id = creator_db_id).first()
    if command:
        return command.id
    else:
        return False

def edit_command(keyword, new_response):
    command = session.query(Command).filter_by(keyword = keyword, channel_id = creator_db_id).first()
    if command:
        response = session.query(Response).filter_by(command_id = command.id).first()
        response.output = new_response
        session.commit()

#exists checkers
def is_operator(username):
    existing_user = session.query(User).filter_by(twitch_username = username).first()
    operator_state = session.query(Configurable).filter_by(creator_id = creator_db_id, alias ='operator_state').first()
    ops =[]
    ops.extend(admins)
    
    if operator_state.value ==1:
        url = f'https://tmi.twitch.tv/group/user/{channel_name}/chatters'
        response = requests.get(url)
        data = response.json()
        ops.extend(data['chatters']['broadcaster'])
        ops.extend(data['chatters']['vips'])
        ops.extend(data['chatters']['moderators'])

    if existing_user:
        existing_operator = session.query(Operator).filter_by(user_id = existing_user.id, creator_id = creator_db_id).first()
        if existing_operator:
            ops.append(existing_user.twitch_username)

    if username in ops:
        return True
    else:
        print(str(ops))
        return False

def is_raffle():
    raffle_state = session.query(Configurable).filter_by(creator_id = creator_db_id, alias='raffle_state').first()
    if raffle_state.value == 1:
        return True
    else:
        return False

def add_operator(username):
    existing_user = session.query(User).filter_by(twitch_username = username).first()
    if existing_user:
        new_operator = Operator(user_id = existing_user.id, creator_id = creator_db_id)
        session.add(new_operator)
        session.commit()
    else:
        new_user = User(twitch_username = username)
        session.add(new_user)
        session.commit()
        new_operator = Operator(user_id = new_user.id, creator_id = creator_db_id)
        session.add(new_operator)
        session.commit()

def remove_operator(username):
    existing_user = session.query(User).filter_by(twitch_username = username).first()
    if existing_user:
        existing_operator = session.query(Operator).filter_by(user_id = existing_user.id, creator_id = creator_db_id).first()
        session.delete(existing_operator)
        session.commit()
    else:
        pass
        
def get_command_output(keyword):
    command = session.query(Command).filter_by(channel_id = creator_db_id, keyword = keyword).first()
    outputs = session.query(Response).filter_by(command_id = command.id).all()
    responses = []
    for output in outputs:
        responses.append(str(output.output))
    response = str(random.choice(responses))
    return response

def get_raffle_keyword():
    raffle_keyword = session.query(Temporary).filter_by(creator_id = creator_db_id, alias = 'raffle_keyword').first()
    return str(raffle_keyword.value)

def add_raffle_participant(username):
    existing_participant = session.query(Temporary).filter_by(alias='raffle_entry', value=username, note=get_raffle_keyword(channel_name), creator_id=creator_db_id).first()
    if not existing_participant:
        new_participant = Temporary(alias='raffle_entry', value=username, note=get_raffle_keyword(channel_name), creator_id=creator_db_id)
        session.add(new_participant)
        session.commit()

def raffle(state, keyword):
    raffle_state = session.query(Configurable).filter_by(creator_id = creator_db_id, alias = 'raffle_state').first()
    raffle_keyword = session.query(Temporary).filter_by(creator_id = creator_db_id, alias = 'raffle_keyword').first()
    if state == 1:
        raffle_state.value = 1
        raffle_keyword.value = keyword
        session.commit()
    else:
        raffle_state.value = 0
        raffle_keyword.value = uuid.uuid4()
        session.commit()

def toggle_ops():
    operator_state = session.query(Configurable).filter_by(creator_id = creator_db_id, alias='operator_state').first()
    if operator_state.value == 1:
        operator_state.value = 0
        session.commit()
        return (f'Operator state is now addop only.')
    else:
        operator_state.value = 1
        session.commit()
        return (f'Moderators and VIPs are now operators of Nurdbot.')

def toggle_mute():
    mute_state = session.query(Configurable).filter_by(creator_id = creator_db_id, alias='mute_state').first()
    if mute_state.value == 1:
        mute_state.value = 0
        session.commit()
        return (f'MrDestructoid Nurdbot personality matrix engaged MrDestructoid')
    else:
        mute_state.value =1
        session.commit()
        return (f'MrDestructoid Nurdbot personality matrix disengaged MrDestructoid')

def get_mute_state():
    mute_state = session.query(Configurable).filter_by(creator_id = creator_db_id, alias='mute_state').first()
    return mute_state.value

def is_harass(username):
    existing_harass = session.query(TwitchHarass).filter_by(creator_id = creator_db_id, username=username).first()
    if existing_harass:
        return True
    else:
        return False

def add_harass(username):
    if is_harass(channel_name, username):
        print(f'{username} is already a harass target.')
    else:
        new_harass = TwitchHarass(creator_id = creator_db_id, username=username)
        session.add(new_harass)
        session.commit()

def remove_harass(username):
    existing_harass = session.query(TwitchHarass).filter_by(creator_id = creator_db_id, username=username).first()
    if existing_harass:
        session.delete(existing_harass)
        session.commit()
    else:
        print(f'{username} is not currently a harass target.')

def sponge_bob_case(message):
    response =""
    for idx in range(len(message)):
        if not idx % 2:
            response = response + message[idx].upper()
        else:
            response = response + message[idx].lower()
    return response

def get_aggression_level():
    aggression = session.query(Configurable).filter_by(creator_id = creator_db_id, alias = 'aggression').first()
    return aggression.value

def set_aggression_level(value):
    aggression = session.query(Configurable).filter_by(creator_id = creator_db_id, alias = 'aggression').first()
    aggression.value = value
    session.commit()

def get_stupidity_level():
    stupidity = session.query(Configurable).filter_by(creator_id = creator_db_id, alias = 'stupidity').first()
    return stupidity.value

def set_stupidity_level(value):
    stupidity = session.query(Configurable).filter_by(creator_id = creator_db_id, alias = 'stupidity').first()
    stupidity.value = value
    session.commit()

def confirm_user(twitch_username):
    is_user = session.query(User).filter_by(twitch_username = twitch_username).first()
    is_discord = session.query(User).filter_by(twitch_username = f'--{twitch_username}').first()
    if is_user:
        is_user.discord_id = is_user.discord_id.lstrip("--")
        session.commit()
    elif is_discord:
        is_discord.twitch_username = is_discord.twitch_username.lstrip("--")
        session.commit()
    else:
        print("Didn't find either, wtf.")

def deduct_user_scrap(username, amount):
    scrap = session.query(Scrap).filter_by(username = username, creator_id = creator_db_id).first()
    if scrap:
        if scrap.amount > amount:
            scrap.amount = scrap.amount - amount
            session.commit()
            return True
        else:
            return False
    else:
        return False

def add_user_scrap(username, amount):
    scrap = session.query(Scrap).filter_by(username = username, creator_id = creator_db_id).first()
    scrap.amount = scrap.amount + amount
    session.commit()

def get_user_scrap(username):
    scrap = session.query(Scrap).filter_by(username = username, creator_id = creator_db_id).first()
    if scrap:
        return f'{username} currently has a balance of {scrap.amount} scrap.'
    else:
        return f'{username} currently has no scrap. :('

#This is all basically now parity with discord
@bot.event
async def event_ready():
    print(f'<DESTROY ALL HUMANS> | {bot.nick}')


#THANKS CSWIL I LOVE YOU SO MUCH
async def event_message(message):
    log_message(message.author.name, message.content)
    #parse for custom commands
    print(f'{Color.blue}<{message.channel.name}>{Color.yellow} {message.author.name} :{Color.white} {message.content}')
    if str(message.content).startswith('!'):
        command_input = str(message.content.split(" ")[0])
        if command_input in get_commands_list():
            await message.channel.send(get_command_output(command_input))
        else:
            #didnt find a dynamicly loaded command, so proceeding to check static ones.
            await bot.handle_commands(message)

    if is_raffle():
        raffle_keyword = get_raffle_keyword()
        if str(message.content).startswith(raffle_keyword):
            add_raffle_participant(message.author.name)
    
    #SH
    sh = any(ele in str(message.content.lower()) for ele in suicide)
    if sh:
        await message.channel.send(f'If you are having suicidal thoughts, please call this number right now. 1-800-273-8255')
    ##TOGGLE MUTEABLE
    if get_mute_state() == 0:
        #trigger forgive stuff
        trigger_forgive = any(ele in str(message.content.lower()) for ele in forgive_cues)
        if trigger_forgive:
            if is_harass(str(message.author.name)):
                remove_harass(str(message.author.name))
                await message.channel.send(f'{random.choice(generic_forgive_messages)} {message.author.name}')

        #trigger harass stuff
        trigger_harass = any(ele in str(message.content.lower()) for ele in harass_cues)
        if trigger_harass:
            if not is_harass(str(message.author.name)):
                add_harass(str(message.author.name))
                await message.channel.send(f'{random.choice(generic_harass_messages)} {message.author.name}')

        if is_harass(str(message.author.name)):
            roll = random.randint(1, get_aggression_level())
            if roll == 1:
                await message.channel.send(sponge_bob_case(str(message.content)))
        
        agree = random.randint(1, get_stupidity_level())
        if agree == 1:
            await message.channel.send('^')
#uwu stuff
        trigger_uwu = any(ele in str(message.content) for ele in uwus)
        trigger_uwu_lower = any(ele.lower() in str(message.content) for ele in uwus)
        if trigger_uwu or trigger_uwu_lower:
            if message.author.name.lower() !='nurdbot':
                roll = random.randint(1,1)
                if roll == 1:
                    await message.channel.send(random.choice(uwus))

            #parse for 69
        if '69' in str(message.content):
            if message.author.name.lower() != 'nurdbot':
                roll = random.randint(1,1)
                if roll == 1:
                    await message.channel.send(random.choice(six_nines))
                else:
                    await bot.handle_commands(message)

#static commands
@bot.command(name='addop', aliases=['deputize'])
async def add_operator_command(ctx):
    if is_operator(ctx.author.name):
        username = str(ctx.message.content).split(' ')
        if is_operator(username[1].lower()):
            await ctx.send(f'{username[1]} is already an operator in this channel. Get it together.')
        else:
            add_operator(username[1].lower())
            await ctx.send(f'Successfully added {username[1]} as an operator of nurdbot.')
    else:
        await ctx.send(f'{random.choice(generic_fail_messages)} {ctx.author.name}')

@bot.command(name='rmop', aliases=['fire'])
async def remove_operator_command(ctx):
    if is_operator(ctx.author.name):
        username = str(ctx.message.content).split(' ')
        remove_operator(username[1].lower())
        await ctx.send(f'Successfully removed {username[1]} as an operator of nurdbot.')
    else:
        await ctx.send(f'{random.choice(generic_fail_messages)} {ctx.author.name}')

@bot.command(name='about', aliases=['commands'])
async def about_command(ctx):
    await ctx.send(f'My commands can be customized for each channel, but - https://nurdbot.dev/about')

@bot.command(name='harass', aliases=['bully', 'mock', 'tease'])
async def harass_command(ctx):
    if is_operator(ctx.author.name):
        username = str(ctx.message.content).split(' ')
        if username[1].lower() =='nurdbot':
            await ctx.send(f'{random.choice(generic_fail_messages)}')
        else:
            add_harass(str(username[1].lower()))
            await ctx.send(f'{random.choice(generic_harass_messages)} {username[1]}')
    else:
        await ctx.send(f'{random.choice(generic_fail_messages)} {ctx.author.name}')

@bot.command(name='forgive')
async def forgive_command(ctx):
    if is_operator(ctx.author.name):
        username = str(ctx.message.content).split(' ')
        remove_harass(str(username[1].lower()))
        await ctx.send(f'{random.choice(generic_forgive_messages)} {username[1]}')
    else:
        await ctx.send(f'{random.choice(generic_fail_messages)} {ctx.author.name}')

@bot.command(name='flipacoin', aliases=['cointoss'])
async def flip_a_coin_command(ctx):
    flip = random.randint(1,2)
    if flip == 1:
        await ctx.send(f'Heads')
    else:
        await ctx.send(f'Tails')

@bot.command(name='followage', aliases=['followtime'])
async def followage_command(ctx):
    url = f'https://api.2g.be/twitch/followage/{ctx.channel.name}/{ctx.author.name}?format=mwdhms'
    async with aio_session.get(url) as response:
        data = await response.text()
    await ctx.send(str(data))

@bot.command(name='uptime')
async def uptime_command(ctx):
    url = f'https://beta.decapi.me/twitch/uptime/{ctx.channel.name}'
    async with aio_session.get(url) as response:
        data = await response.text()
    await ctx.send(f'Current uptime for {ctx.channel.name} is {data}')

@bot.command(name='insult')
async def insult_command(ctx):
    url ='https://insult.mattbas.org/api/insult'
    async with aio_session.get(url) as response:
        data = await response.text()
    await ctx.send(f'{data} {ctx.author.name}')

@bot.command(name='compliment')
async def compliment_command(ctx):
    url ='https://complimentr.com/api'
    async with aio_session.get(url) as response:
        data = await response.json()
        output = str(data['compliment'])
    await ctx.send(f'{output} {ctx.author.name}')

@bot.command(name='hotness')
async def hotness_command(ctx):
    if ctx.author.name == 'pronerd_jay':
        await ctx.send('I\'d give you a 10/10.')
    else:
        roll = random.randint(1,10)
        await ctx.send(f'{ctx.author.name} id give you a {str(roll)}/10')

@bot.command(name='raffle')
async def raffle_command(ctx):
    if is_operator(ctx.author.name):
        parse = ctx.message.content.split(" ")
        if len(parse) < 2:
            await ctx.send('Didn\'t find a keyword. Try !raffle KEYWORD')
        else:
            keyword = parse[1].strip()
            raffle(1, keyword)
            await ctx.send(f'Raffle has started, type {keyword} once to enter.')

@bot.command(name='draw')
async def draw_command(ctx):
    if is_operator(ctx.author.name):
        #!TODO FIX ME, THIS IS FUCKING WEIRD.
        if is_raffle():
            count = ctx.message.content.split(" ")
            #Thanks twitch.tv/Rattaeb
            if len(count) > 1:
                if count[1].strip().isdigit():
                    amount = int(count[1])
                else:
                    amount = 1
            else:
                amount = 1
            raffle_keyword = get_raffle_keyword()
            people = session.query(Temporary).filter_by(alias='raffle_entry',note=raffle_keyword, creator_id=creator_db_id).all()
            pool =[]
            for person in people:
                pool.append(person.value)
            #set the raffle to closed state
            raffle(0, raffle_keyword)
            #present the winner
            message = 0
            previous = []
            while amount > message:
                winner = random.choice(pool)
                pool.remove(winner)
                await ctx.send(winner)
                message = message +1
            #await ctx.send(winner)

@bot.command(name='roll')
async def roll_dice_command(ctx):
    amount = str(ctx.content.split(" ")[1])
    try:
        result = dice.roll(amount)
        await ctx.send(f'{ctx.author.name} asked for {amount} - {result}')
    except:
        await ctx.send(f'{random.choice(generic_fail_messages)} {ctx.author.name}.')

@bot.command(name='addcommand')
async def add_command_command(ctx):
    if is_operator(ctx.author.name):
        channel_name = str(ctx.channel.name)
        keyword_raw = str(ctx.content.split(" ")[1])
        if keyword_raw[0] == '!':
            keyword = keyword_raw
        else:
            keyword = f'!{keyword_raw}'
        response = str(ctx.content.split(f'{keyword_raw} ')[1])
        if get_command_id(keyword) == False:
            if keyword in static_commands:
                await ctx.send(f'Sorry we already have that command, try using {keyword}')
            else:
                insert_command(keyword, response)
                await ctx.send(f'Successfully added {keyword} for {channel_name}\'s twitch chat')
        else:
            await ctx.send(f'I already have a command of {keyword} try !editcommand or !addresponse')
    else:
        print('this person wasnt an operator. Huh.')

@bot.command(name='editcommand')
async def edit_command_command(ctx):
    if is_operator(ctx.author.name):
        channel_name = str(ctx.channel.name)
        keyword = str(ctx.content.split(" ")[1])
        new_response = str(ctx.content.split(keyword)[1])
        if keyword in static_commands:
            await ctx.send(f'Sorry we can\'t edit the static commands')
        else:
            edit_command(keyword, new_response)
            await ctx.send(f'Successfully changed {keyword} for {channel_name}\'s twitch chat.')
        
@bot.command(name='addresponse')
async def add_response_command(ctx):
    if is_operator(ctx.author.name):
        channel_name = str(ctx.channel.name)
        keyword = str(ctx.content.split(" ")[1])
        response = str(ctx.content.split(f'{keyword} ')[1])
        if keyword in static_commands:
            await ctx.send(f"Sorry I can't add a response to a static command.")
        else:
            if get_command_id(keyword) == False:
                await ctx.send(f"Sorry I didn't find a command with {keyword} listed for this channel.")
            else:
                insert_response(get_command_id(keyword), response)
                await ctx.send(f"Response for {keyword} has been added.")

@bot.command(name='toggleops')
async def toggle_ops_command(ctx):
    if is_operator(ctx.author.name):
        await ctx.send(toggle_ops())
    else:
        await ctx.send(f"{random.choice(generic_fail_messages)} {ctx.author.name}")

@bot.command(name='togglemute', aliases=['mute', 'shutup', 'hush'])
async def toggle_mute_command(ctx):
    if is_operator(ctx.author.name):
        await ctx.send(toggle_mute())
    else:
        await ctx.send(f'{random.choice(generic_fail_messages)} {ctx.author.name}')

@bot.command(name='aggression')
async def set_aggression_command(ctx):
    if is_operator(ctx.author.name):
        value = str(ctx.message.content).split(" ")
        if len(value) > 1:
            if value[1].isdigit():
                set_aggression_level(int(value[1]))
                await ctx.send(f'Aggression matrix successfully set to {value[1]}')
            else:
                await ctx.send(f'Aggression parameter needs to be number.')
        else:
            await ctx.send(f'Missing value parameter for this command.')
    else:
        await ctx.send(f"{random.choice(generic_fail_messages)} {ctx.author.name}")

@bot.command(name='stupidity')
async def set_stupidity_level_command(ctx):
    if is_operator(ctx.author.name):
        value = str(ctx.message.content).split(" ")
        if len(value) > 1:
            if value[1].isdigit():
                set_stupidity_level(int(value[1]))
                await ctx.send(f'Stupidity matrix successfully set to {value[1]}')
            else:
                await ctx.send(f'Stupidity parameter needs to be a number.')
        else:
            await ctx.send(f'Missing value parameter for this command.')
    else:
        await ctx.send(f"{random.choice(generic_fail_messages)} {ctx.author.name}")

@bot.command(name='tether')
async def confirm_tether(ctx):
    confirm_user(str(ctx.author.name))
    await ctx.send(f"You are now tethered to your discord account MrDestructoid")

@bot.command(name='shoutout', aliases=['so'])
async def shoutout_command(ctx):
    if is_operator(ctx.author.name):
        value = str(ctx.message.content).split(" ")
        if len(value)> 1:
            await ctx.send(f'Be sure to check out {value[1]}! https://twitch.tv/{value[1]}')
    else:
        await ctx.send(f"{random.choice(generic_fail_messages)} {ctx.author.name}")

#CREDITS:
#THANKS nzeeshan @twitch
@bot.command(name='roadtrip')
async def roadtrip_command(ctx):
    if deduct_user_scrap(ctx.author.name, 1):
        async with aio_session.get('https://api.3geonames.org/?randomland=yes') as response:
            trip_data = minidom.parseString(await response.text())
        destination = trip_data.getElementsByTagName('wikipedia')
        if destination:
            location = str(destination[0].firstChild.nodeValue).split(':')[1]
            try:
                summary = wikipedia.summary(location)
                add_user_scrap(ctx.author.name, 69)
                await ctx.send(summary)
            except:
                add_user_scrap(ctx.author.name, 1)
                await ctx.send(random.choice(no_wiki_entry))
        else:
            await ctx.send(random.choice(i_got_lost))
    else:
        await ctx.send(random.choice(not_enough_scrap))

@bot.command(name='balance')
async def scrap_balance_command(ctx):
    await ctx.send(get_user_scrap(ctx.author.name))

#fixme...m8

#//THIS WONT WORK UINTIL WE ONBOARD THIS COMMAND FOR EVERYONE. PLEASE DO NOT PUSH. !FUCK !TODO !HELP !MOM !SOMEONE STOP ME
@bot.command(name='addquote')
async def add_quote_command(ctx):
    text_input = ctx.message.content.split('!addquote ')[1]
    command_id = get_command_id('quote')
    if not command_id:
        insert_command('quote', text_input)
    else:
        insert_response(command_id, text_input) 

    await ctx.send(f'{random.choice(generic_success_messages)}')

@bot.command(name='quote', aliases=['qoute'])
async def quote_command(ctx):
    await ctx.send(get_command_output('quote'))

#special jay only stuff
@bot.command(name='todo')
async def todo_command(ctx):
    if ctx.channel.name == 'pronerd_jay' and ctx.author.name =='pronerd_jay':
        text_input = ctx.message.content.split('!todo ')[1]
        url = f'http://prime-sub:8420/'
        async with aio_session.post(url, json={'title': f'{text_input}'}):
            print('uwu thanks nix')

        await ctx.send(f'{random.choice(generic_success_messages)}')

@bot.command(name='done', aliases=['nailedit', 'completed', 'yeettask'])
async def done_command(ctx):
    if ctx.channel.name == 'pronerd_jay' and ctx.author.name == 'pronerd_jay':
        text_input = ctx.message.content.split(' ')[1]
        item_number = int(text_input)
        url = f'http://prime-sub:8420/{item_number}'
        async with aio_session.delete(url):
            print('uwu deletely weety')
        await ctx.send(f"{random.choice(generic_success_messages)}")

@bot.command(name='clear')
async def clear_todo_command(ctx):
    if ctx.channel.name == 'pronerd_jay' and ctx.author.name == 'pronerd_jay':
        url = f'http://prime-sub:8420/'
        async with aio_session.get(url) as all_tasks:
            for task in all_tasks:
                task_url = f"http://prime-sub:8420/{task['id']}"
                async with aio_session.delete(task_url):
                    print(f"uwu deleted {task['id']}")

        await ctx.send(f"{random.choice(generic_success_messages)}")
    else:
        await ctx.send(f"{random.choice(generic_fail_messages)} {ctx.author.name}")


#run the bot.
bot.run()

 
