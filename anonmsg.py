import logging
import discord  # Using legacy 0.16.12
import asyncio
import colorsys # Used to convert from hsv to rgb
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


def get_colour(message_number):  # Dynamic embed colour - Generates a rainbow of colours using a triangle wave with a period of 360 messages.
    triangle_wave = lambda m: 90 - abs(m % 180 - 90)
    hue = (triangle_wave(message_number)/90) 
    colour = colorsys.hsv_to_rgb(hue, 1, 1) # Saturation and value are always at 1 for maximum intensity
    hex_colour_str = "0x%02x%02x%02x" % (int(colour[0] * 255), int(colour[1] * 255), int(colour[2] * 255))
    return int(hex_colour_str, 16)


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
        return
    help_em.add_field(name="anon.info", value="Returns some basic info about the bot.")
    help_em.add_field(name="anon.send [message]", value="Submit a message to be sent, anonymously. DM only.")
    help_em.add_field(name="anon.review", value="[Mod] Approve or deny submitted messages.")
    help_em.add_field(name="anon.output [channel]", value="[Mod] Change the output channel for messages.")
    help_em.add_field(name="anon.notif [channel]", value="[Mod] Get nofified of approvals in a specific channel.")
    help_em.add_field(name="anon.mutedrole [role]", value="[Mod] This role will not be allowed to send messages via the bot.")
    await bot.say(embed=help_em)


@bot.command(pass_context=True)
async def info(ctx):
    em = discord.Embed(title="Bot Information", color=0x8B008B)
    em.set_thumbnail(url=bot.user.avatar_url)
    em.set_author(name=str(ctx.message.author), icon_url=ctx.message.author.avatar_url)
    em.set_footer(text="Created by Keegan#9109")

    uptime = time2string(datetime.utcnow() - bot.start_time)
    em.add_field(name="Uptime:", value=uptime)

    total_users = 1
    for serv_obj in bot.servers:
        total_users += serv_obj.member_count - 1
    em.add_field(name="Reach:", value="{} users on {} servers".format(total_users, len(bot.servers)))

    with open("settings.txt") as file:
        line = str(file.readline()).split()

    names = ["Output Channel", "Notify Channel"]
    for num in range(2):
        chl = bot.get_channel(line[num])
        if chl is None:
            val = "Not Set"
        else:
            val = chl.mention
        em.add_field(name=names[num], value=val)

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

    with open("settings.txt") as s:
        line = str(s.readline()).split()

    out_chl = bot.get_channel(line[0])
    if out_chl is None:
        await bot.say("Currently, no output channel is set by the server.")
        return
    notif_chl = bot.get_channel(line[1])
    member_of_user = out_chl.server.get_member(ctx.message.author.id)

    if out_chl.server.me.server_permissions.ban_members:
        ban_list = await bot.get_bans(out_chl.server)
        if member_of_user in ban_list:
            await bot.say("Sorry, you're currently banned from that server.")
            return
    elif line[2] != "NULL":  # Mute Check (if role set)
        role_list = out_chl.server.roles
        role_obj = None
        for role in role_list:
            if line[2] == role.id:
                role_obj = role
                break
        if role_obj is not None:
            if role_obj in member_of_user.roles:
                await bot.say("Sorry, you're currently muted in that server.")
                return
        elif notif_chl is not None:
            await bot.send_message(notif_chl, "The muted role was not found. WARNING: "
                                              "People who are muted will still be able to submit messages. "
                                              "Disable or re-assign the role with 'anon.mutedrole'.")

    print(statement)
    statement = statement.replace('\n', '¬')
    with open("queue.txt", "a", encoding="utf-8") as q:
        q.write('"{0}"\n'.format(statement))
    await bot.say("Your message has been submitted! You won't be able to send another one for 5 minutes, to prevent spam.")

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
    out_chl = bot.get_channel(line[0])
    if out_chl is None:
        em = discord.Embed(description="No output channel has been set with 'anon.output'.")
        await bot.edit_message(review_msg, embed=em)
        return
    for i in range(len(number)):
        with open('queue.txt', 'r', encoding='utf-8') as q:
            data = q.read().splitlines(True)
        em.clear_fields()
        em.add_field(name="Remaining", value=str(len(data)))
        em.add_field(name="Output Channel", value=out_chl.mention)
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
            send_em = discord.Embed(colour=get_colour(int(line[3])), description=statement + '- Anonymous')
            send_em.set_footer(text="#" + line[3])
            await bot.send_message(out_chl, embed=send_em)
            line[3] = str(int(line[3]) + 1)
            with open('settings.txt', 'w') as update:
                update.write(" ".join(line))
    em = discord.Embed(description="There are no more messages to approve at the moment.")
    await bot.edit_message(review_msg, embed=em)


def update_settings(position, new_string):
    with open("settings.txt") as settings_r:
        line = str(settings_r.readline()).split()
    line[position] = new_string
    with open("settings.txt", "w") as settings_w:
        settings_w.write(" ".join(line))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def output(ctx, *, target=None):
    """Sets where you want to output anonymous messages on the server, when approved.

            output <text_channel> --> updates channel to the specified parameter. If none is given, removes output.
    """

    if target is None:
        update_settings(0, "NULL")
        await bot.say("Output channel removed.")
        return
    if len(ctx.message.channel_mentions) != 1:
        await bot.say("Channel not found. Make sure you pass through the channel mention, not the name.")
        return
    log_chl = ctx.message.channel_mentions[0]
    update_settings(0, log_chl.id)
    await bot.say("Output channel updated to: {}".format(log_chl.mention))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def notif(ctx, *, target=None):  # Notify in a specific channel when a new item is in the queue (or added to it?)
    """Sets where you want to be notified of new anonymous messages to approve on the server.

        notif <text_channel> --> updates channel to the specified parameter. If none is given, removes notifications.
    """

    if target is None:
        update_settings(1, "NULL")
        await bot.say("Notify channel removed.")
        return
    if len(ctx.message.channel_mentions) != 1:
        await bot.say("Channel not found. Make sure you pass through the channel mention, not the name.")
        return
    log_chl = ctx.message.channel_mentions[0]
    update_settings(1, log_chl.id)
    await bot.say("Notify channel updated to: {}".format(log_chl.mention))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def mutedrole(ctx, *, target=None):

    if target is None:
        update_settings(1, "NULL")
        await bot.say("Muted role unassigned.")
        return
    if len(ctx.message.role_mentions) != 1:
        await bot.say("Role not found. Make sure you enable and reference the role mention, not the name.")
        return
    log_chl = ctx.message.role_mentions[0]
    update_settings(2, log_chl.id)
    await bot.say("Muted role updated to: {}".format(log_chl.mention))


if __name__ == "__main__":
    try:
        bot.run('token here')
    except err.HTTPException:
        print("Discord seems to be experiencing some problems right now :/")
