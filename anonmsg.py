import logging
import discord # Using legacy 0.16.12
import asyncio
from discord import errors as err
from discord.ext import commands
from discord.ext.commands import CheckFailure, MissingRequiredArgument
from datetime import datetime, timedelta
from math import floor


def time2string(time: timedelta):
    """Converts to highest time denomination, rounded down."""
    multipliers = [60, 60, 24, 7, 52]
    denominations = ["seconds", "minutes", "hours", "days", "weeks", "years"]

    current = 1
    for num in range(6):
        diff = int(floor(time / timedelta(seconds=current)))
        if diff >= multipliers[num] and num < 5:
            current *= multipliers[num]
        else:
            return "{} {}".format(str(abs(diff)), denominations[num])


logging.basicConfig(level=logging.INFO)
bot = commands.Bot(command_prefix="anon.", description='''Send anonymous messages, with optional moderator approval''')
bot.remove_command('help')
bot.cooldown = []

bot.start_time = datetime.utcnow()


@bot.event
async def on_ready():
    print("{0} is online.".format(bot.user))
    await bot.change_presence(game=discord.Game(name="'anon.help' to start!"))


@bot.event
async def on_command_error(error, ctx):
    print(error)
    if isinstance(error, CheckFailure):
        print("User Permission Error.")
        err_text = "Sorry, you don't have the required permissions for this command."
        err_react = "\U0001F6AB"

    elif isinstance(error, MissingRequiredArgument):  # Clean up repetitive code
        print("Argument Error.")
        err_text = "Missing a required argument. Try the help command for more info."
        err_react = "\U000026A0"

    elif isinstance(error, err.Forbidden):
        print("Bot Permission Error.")
        err_text = "It seems the bot doesn't have the permissions to execute this command."
        err_react = "\U0001F916"

    else:
        try:
            await bot.add_reaction(ctx.message, "\U00002753")  # Question Mark
            # If other error encountered - attach '?' reaction to message
        except discord.errors.NotFound:
            print("Original Message Deleted.")
        finally:
            print(error)
            return
    err_msg = await bot.send_message(ctx.message.channel, err_text)
    await bot.add_reaction(ctx.message, err_react)
    await asyncio.sleep(5)  # Delete message after 5 secs
    await bot.delete_message(err_msg)


async def perm_check(ctx):  # Checks whether the user can send messages in the output channel, for a single server.
    with open("settings.txt") as file:
        line = str(file.readline())
        out_chl_id = line.split()[0]
    out_chl = bot.get_channel(out_chl_id)  # Output channel needed to function (could be deleted)
    member_of_user = out_chl.server.get_member(ctx.message.author.id)
    if member_of_user is not None and out_chl.permissions_for(member_of_user).manage_messages:
        return True
    return False


def get_colour(message_number):  # Dynamic embed colour - changes every 50 messages, starting at 100.
    colours = [0xFF3333, 0xFF9933, 0xFFFF33, 0x99FF33, 0x3399FF, 0x9933FF, 0xFF33FF, 0xFF3399, 0xFFFFFF, 0x000000]
    if message_number < 100:
        return 0x4f545c
    message_number -= 100
    message_number = message_number % 500
    return colours[(message_number // 50)]


@bot.command(pass_context=True)
async def help(ctx, *, cmd=None):
    """Did you really just use the help command to try and figure out how to use the help command?

    I'll give you points for ingenuity, I suppose...
    """
    help_em = discord.Embed(colour=0x8B008B, description="Submit messages to be sent, anonymously.")
    help_em.set_thumbnail(url=bot.user.avatar_url)
    help_em.set_author(name=str(ctx.message.author), icon_url=ctx.message.author.avatar_url)
    help_em.set_footer(text="Type anon.help [command] for more information.")
    if cmd is not None:
        doc_str = bot.get_command(cmd).help
        help_em.description = doc_str
        await bot.say(embed=help_em)
    else:
        help_em.add_field(name="anon.info", value="Returns some basic info about the bot.")
        help_em.add_field(name="anon.send [message]", value="Submit a message to be sent, anonymously. "
                                                            "DM only.")
        if await perm_check(ctx):
            help_em.add_field(name="anon.review", value="[Mod] Approve or deny submitted messages.")
            help_em.add_field(name="anon.output [channel]", value="[Mod] Change the output channel for messages.")
            help_em.add_field(name="anon.notif [channel]", value="[Mod] Get nofified of approvals in a specific channel.")
        await bot.say(embed=help_em)


@bot.command(pass_context=True)
async def info(ctx):
    em = discord.Embed(title="Bot Information", color=0x8B008B)
    em.set_thumbnail(url=bot.user.avatar_url)
    em.set_author(name=str(ctx.message.author), icon_url=ctx.message.author.avatar_url)
    uptime = time2string(datetime.utcnow() - bot.start_time)
    em.add_field(name="Uptime:", value=uptime)
    total_users = 1
    for serv_obj in bot.servers:
        total_users += serv_obj.member_count - 1
    em.add_field(name="Reach:", value="{} users on {} servers".format(total_users, len(bot.servers)))
    with open("settings.txt") as file:
        line = str(file.readline()).split()
    em.add_field(name="Output Channel", value=bot.get_channel(line[0]).mention)
    if await perm_check(ctx):
        notif_channel = bot.get_channel(line[1])
        if notif_channel is None:
            val = " "
        else:
            val = notif_channel.mention
        em.add_field(name="Notify Channel", value=val)
    em.set_footer(text="Created by Keegan#9109")
    await bot.say(embed=em)


@bot.command(pass_context=True)
async def send(ctx, *, statement=None):
    """Submits your message to be sent to a Discord channel, anonymously.

    If you'd like to know the exact channel and settings.txt, try the anon.info command.
    To protect your anonymity, if your message is rejected you won't be notified.
    Please keep in mind custom server emojis won't show as the bot isn't in those servers.

    anon.send [statement] --> sends [statement] to the specified Discord channel.
    """
    if ctx.message.channel.type.name == "text":
        await bot.say("This command can only be used when directly messaging me.")
        return
    elif ctx.message.author.id in bot.cooldown:
        await bot.say("You've already sent a message in the last 5 minutes.")
        return
    elif statement is None:
        await bot.say("You haven't typed anything to send!")
        return
    elif len(statement) > 1500:
        await bot.say("We have a character limit of 1500, to make sure Discord doesn't shout at us when transferring your message D:")
        return
    elif "¬" in statement:
        await bot.say("Sorry, you can't send a message with the ¬ character in.")
        return
    print(statement)
    statement = statement.replace('\n', '¬')
    with open("queue.txt", "a", encoding="utf-8") as q:
        q.write('"{0}"\n'.format(statement))
    await bot.say("Your message has been submitted! You won't be able to send another one for 5 minutes, to prevent spam.")

    with open("settings.txt") as s:
        line = str(s.readline()).split()
    notif_chl = bot.get_channel(line[1])
    if notif_chl != "NULL":
        with open('queue.txt', 'r', encoding='utf-8') as q:
            number = q.read().splitlines(True)
        await bot.send_message(notif_chl, "There are {0} anonymous messages to review. Type 'anon.review' to start.".format(len(number)))
    bot.cooldown.append(ctx.message.author.id)
    await asyncio.sleep(300)
    bot.cooldown.remove(ctx.message.author.id)


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def review(ctx):
    em = discord.Embed(colour=0xFFD700)
    em.set_author(name="Approve or Deny Messages", icon_url=bot.user.avatar_url)
    em.set_footer(text="Approvals time out after 30 seconds of inactivity.")
    review_msg = await bot.say(embed=em)

    with open('queue.txt', 'r', encoding='utf-8') as q:
        number = q.read().splitlines(True)
    with open('settings.txt') as s:
        line = str(s.readline()).split()

    for i in range(len(number)):
        with open('queue.txt', 'r', encoding='utf-8') as q:
            data = q.read().splitlines(True)
        em.clear_fields()
        em.add_field(name="Remaining", value=str(len(data)))
        em.add_field(name="Output Channel", value=bot.get_channel(line[0]).mention)
        statement = data[0].replace('¬', '\n')
        em.add_field(name="Message", value=statement)
        await bot.edit_message(review_msg, embed=em)
        await bot.add_reaction(review_msg, "\U00002705")
        await bot.add_reaction(review_msg, "\U0000274C")
        response = await bot.wait_for_reaction(["\U00002705", "\U0000274C"], user=ctx.message.author, timeout=30, message=review_msg)
        await bot.clear_reactions(review_msg)
        if response is None:
            return

        # Deletes first line of queue
        with open('queue.txt', 'w', encoding='utf-8') as w:
            w.writelines(data[1:])
        if response.reaction.emoji == "\U00002705":
            send_em = discord.Embed(colour=get_colour(int(line[2])), description=statement + '- Anonymous')
            send_em.set_footer(text="#" + line[2])
            await bot.send_message(bot.get_channel(line[0]), embed=send_em)
            line[2] = str(int(line[2]) + 1)
            with open('settings.txt', 'w') as update:
                update.write("{0} {1} {2}".format(line[0], line[1], line[2]))
    em = discord.Embed(description="There are no more messages to approve at the moment.")
    await bot.edit_message(review_msg, embed=em)


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def output(ctx, *, target=None):  # Notify in a specific channel when a new item is in the queue (or added to it?)
    """Sets where you want to output anonymous messages on the server, when approved.

            output <text_channel> --> updates channel to the specified parameter. If none is given, removes notifications.
        """
    if len(ctx.message.channel_mentions) == 1:
        log_channel = ctx.message.channel_mentions[0]
        log_chl_id = log_channel.id
        log_chl_mention = log_channel.mention
    elif target is None:
        await bot.say("An output channel is required.")
        return
    else:
        await bot.say("Channel not found. Make sure you pass through the channel reference or ID, not the name.")
        return

    with open('queue.txt', 'r', encoding='utf-8') as q:
        number = q.read().splitlines(True)
    with open("settings.txt") as s:
        line = str(s.readline()).split()
    line[0] = log_chl_id
    with open("settings.txt", "w") as over:
        over.write(("{0} {1} {2}".format(line[0], line[1], line[2])))

    await bot.say("Output channel updated to: {}".format(log_chl_mention))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def notif(ctx, *, target=None):
    """Sets where you want to be notified of new anonymous messages to approve on the server.

        notif <text_channel> --> updates channel to the specified parameter. If none is given, removes notifications.
    """
    if len(ctx.message.channel_mentions) == 1:
        log_channel = ctx.message.channel_mentions[0]
        log_chl_id = log_channel.id
        log_chl_mention = log_channel.mention
    elif target is None:
        log_chl_id = "NULL"
        log_chl_mention = "None set."

    else:
        await bot.say("Channel not found. Make sure you pass through the channel reference or ID, not the name.")
        return

    with open("settings.txt") as s:
        line = str(s.readline()).split()
    line[1] = log_chl_id
    with open("settings.txt", "w") as over:
        over.write(("{0} {1} {2}".format(line[0], line[1], line[2])))

    await bot.say("Notify channel updated to: {}".format(log_chl_mention))

if __name__ == "__main__":
    try:
        bot.run('token here')
    except err.HTTPException:
        print("Discord seems to be experiencing some problems right now :/")
