import logging
import json
import discord  # Using legacy 0.16.12
import asyncio
from colorsys import hsv_to_rgb
from random import choice
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

    with open("queue.json", "r", encoding="utf-8") as file_queue_r:
        queue = json.loads(file_queue_r.read())

    file_servers = set(queue.keys())
    curr_servers = set()
    for svr in bot.servers:
        curr_servers.add(svr.id)

    to_add = curr_servers - file_servers
    to_remove = file_servers - curr_servers
    if to_add == to_remove:
        print("No servers were added/removed while offline.")
        return

    if to_add != set():
        for add_id in to_add:
            queue[add_id] = []
    if to_remove != set():
        for remove_id in to_remove:
            queue.pop(remove_id)

    with open("queue.json", "w", encoding="utf-8") as file_queue_w:
        file_queue_w.write(json.dumps(queue))


@bot.event
async def on_server_join(svr):
    with open("queue.json", "r+", encoding="utf-8") as file_queue:
        queue = json.loads(file_queue.read())
        queue[svr.id] = []
        file_queue.write(json.dumps(queue))


@bot.event
async def on_server_remove(svr):
    with open("queue.json", "r+", encoding="utf-8") as file_queue:
        queue = json.loads(file_queue.read())
        queue.pop(svr.id)
        file_queue.write(json.dumps(queue))


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


def get_colour(message_number):
    # Generates a rainbow of colours using a linear function with a period of 360 messages.
    hue = ((message_number % 360) / 360)
    colour = hsv_to_rgb(hue, 1, 1)  # Saturation and value are always at 1 for maximum intensity
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
    help_em.add_field(name="anon.output {channel}", value="[Mod] Change the output channel for messages.")
    help_em.add_field(name="anon.notif {channel}", value="[Mod] Get nofified of approvals in a specific channel.")
    help_em.add_field(name="anon.mutedrole {role}",
                      value="[Mod] This role will not be allowed to send messages via the bot.")
    help_em.add_field(name="anon.signoff {message}", value="[Mod] Customise the sign-off below each message.")
    help_em.add_field(name="anon.counter {num}", value="[Mod] Reset the counter, or set to a specific value.")
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

    with open("settings.json") as settings_r:
        content = json.loads(settings_r.read())

    names = ["Output Channel", "Notify Channel"]
    json_names = ["outputChannel", "notifyChannel"]
    for num in range(2):
        chl = bot.get_channel(content[json_names[num]])
        if chl is None:
            val = "Not Set"
        else:
            val = chl.mention
        em.add_field(name=names[num], value=val)

    await bot.say(embed=em)


@bot.command(pass_context=True)
async def send(ctx, *, statement=None):
    """Submits your message to be sent to a Discord channel, anonymously.

    If you'd like to know the exact channel and settings, try the anon.info command.
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
    elif len(statement) > 1000:
        await bot.say(
            "We have a character limit of 1000, to make sure Discord doesn't shout at us when transferring your message D:")
        return

    with open("settings.json") as file_settings:
        settings = json.loads(file_settings.read())

    out_chl = bot.get_channel(settings["outputChannel"])
    if out_chl is None:
        await bot.say("Currently, no output channel is set by the server.")
        return
    notif_chl = bot.get_channel(settings["notifyChannel"])
    member_of_user = out_chl.server.get_member(ctx.message.author.id)

    if out_chl.server.me.server_permissions.ban_members:
        ban_list = await bot.get_bans(out_chl.server)
        if member_of_user in ban_list:
            await bot.say("Sorry, you're currently banned from that server.")
            return
    elif settings["mutedRole"] is not None:  # Mute Check (if role set)
        role_list = out_chl.server.roles
        role_obj = None

        for role in role_list:
            if settings["mutedRole"] == role.id:
                role_obj = role
                break

        if role_obj is not None:
            if role_obj in member_of_user.roles:
                await bot.say("Sorry, you're currently muted in that server.")
                return
        elif notif_chl is not None:
            await bot.send_message(notif_chl, "WARNING: Muted role not found - "
                                              "Members who are muted will still be able to submit messages. "
                                              "Disable or re-assign the role with 'anon.mutedrole'.")

    print(statement)
    print(out_chl.id)
    entry = {"outputChannel": out_chl.id, "content": '"{0}"'.format(statement)}
    with open("queue.json", "r", encoding="utf-8") as file_queue_r:
        queue = json.loads(file_queue_r.read())
        queue[out_chl.server.id].append(entry)
    with open("queue.json", "w", encoding="utf-8") as file_queue_w:
        file_queue_w.write(json.dumps(queue))
    await bot.say(
        "Your message has been submitted! You won't be able to send another one for 5 minutes, to prevent spam.")

    if notif_chl is not None:
        await bot.send_message(notif_chl,
                               "There are {0} anonymous messages to review. Type 'anon.review' to start.".format(
                                   len(queue[out_chl.server.id])))
    bot.cooldown.append(ctx.message.author.id)
    await asyncio.sleep(300)
    bot.cooldown.remove(ctx.message.author.id)


def random_signoff():
    choices = ["Armadillo", "Almond", "Anchovy", "Apple", "Antlion", "Auctioneer", "Ancient", "Anteater", "Anglerfish",
               "Antithesis", "Avocado", "Axiom", "Athlete", "Activist", "Acquaintance", "Acrobat", "Aeroplane", "Alien",
               "Alcoholic", "Aunt"]
    return "- Anonymous " + choice(choices)


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def review(ctx):
    if ctx.message.channel.type.name != "text":
        await bot.say("This command can only be used in a server.")
        return

    em = discord.Embed(colour=0xFFD700)
    em.set_author(name="Approve or Deny Messages", icon_url=bot.user.avatar_url)
    em.set_footer(text="Approvals time out after 30 seconds of inactivity.")
    review_msg = await bot.say(embed=em)

    with open("settings.json") as file_settings:
        settings = json.loads(file_settings.read())
    # Should be removed when multiple outputs per server are introduced
    out_chl = bot.get_channel(settings["outputChannel"])

    if out_chl is None:
        em = discord.Embed(description="No output channel has been set with 'anon.output'.")
        await bot.edit_message(review_msg, embed=em)
        return
    # Removal ends here

    with open('queue.json', 'r', encoding='utf-8') as file_queue_r:
        queue = json.loads(file_queue_r.read())
        svr_queue = queue[ctx.message.server.id]

    flag = False
    svr_queue_copy = []
    for item in svr_queue:
        svr_queue_copy.append(item)

    for entry in svr_queue:
        print(entry)
        print(svr_queue_copy)
        em.clear_fields()
        em.add_field(name="Remaining", value=str(len(svr_queue_copy)))
        out_chl = bot.get_channel(entry["outputChannel"])
        if out_chl is None:
            flag = True
            await bot.say("A message was skipped, as no output channel was set for it.")
            continue

        em.add_field(name="Output Channel", value=out_chl.mention)
        em.add_field(name="Message", value=entry["content"])
        await bot.edit_message(review_msg, embed=em)
        await bot.add_reaction(review_msg, "\U00002705")
        await bot.add_reaction(review_msg, "\U0000274C")
        response = await bot.wait_for_reaction(["\U00002705", "\U0000274C"], user=ctx.message.author, timeout=30,
                                               message=review_msg)
        await bot.clear_reactions(review_msg)
        if response is None:
            queue[ctx.message.server.id] = svr_queue_copy
            with open('queue.json', 'w', encoding='utf-8') as file_queue:
                file_queue.write(json.dumps(queue))
            with open("settings.json", "w") as settings_w:
                settings_w.write(json.dumps(settings))
            return

        # Deletes first line of queue
        svr_queue_copy.pop(0)
        if response.reaction.emoji == "\U00002705":
            send_em = discord.Embed(colour=get_colour(settings["counter"]),
                                    description="{0}\n{1}".format(entry["content"],
                                                                  settings["signoff"] or random_signoff()))
            send_em.set_footer(text="#{0}".format(settings["counter"]))
            await bot.send_message(out_chl, embed=send_em)
            settings["counter"] += 1
            await asyncio.sleep(0.5)

    queue[ctx.message.server.id] = svr_queue_copy
    with open('queue.json', 'w', encoding='utf-8') as file_queue:
        file_queue.write(json.dumps(queue))
    with open("settings.json", "w") as settings_w:
        settings_w.write(json.dumps(settings))
    if flag:
        em = discord.Embed(description="One or more messages were skipped, as no output channel was set for them.")
    else:
        em = discord.Embed(description="There are no more messages to approve at the moment.")

    await bot.edit_message(review_msg, embed=em)


def update_settings(position, new_var):
    with open("settings.json") as settings_r:
        content = json.loads(settings_r.read())
    content[position] = new_var
    with open("settings.json", "w") as settings_w:
        settings_w.write(json.dumps(content))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def output(ctx, *, target=None):
    """Sets where you want to output anonymous messages on the server, when approved.

            output <text_channel> --> updates channel to the specified parameter. If none is given, removes output.
    """

    if target is None:
        update_settings("outputChannel", None)
        await bot.say("Output channel removed.")
        return
    if len(ctx.message.channel_mentions) != 1:
        await bot.say("Channel not found. Make sure you pass through the channel mention, not the name.")
        return
    log_chl = ctx.message.channel_mentions[0]
    update_settings("outputChannel", log_chl.id)
    await bot.say("Output channel updated to: {}".format(log_chl.mention))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def notif(ctx, *, target=None):  # Notify in a specific channel when a new item is in the queue (or added to it?)
    """Sets where you want to be notified of new anonymous messages to approve on the server.

        notif <text_channel> --> updates channel to the specified parameter. If none is given, removes notifications.
    """

    if target is None:
        update_settings("notifyChannel", None)
        await bot.say("Notify channel removed.")
        return
    if len(ctx.message.channel_mentions) != 1:
        await bot.say("Channel not found. Make sure you pass through the channel mention, not the name.")
        return
    log_chl = ctx.message.channel_mentions[0]
    update_settings("notifyChannel", log_chl.id)
    await bot.say("Notify channel updated to: {}".format(log_chl.mention))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def mutedrole(ctx, *, target=None):
    if target is None:
        update_settings("mutedRole", None)
        await bot.say("Muted role unassigned.")
        return
    if len(ctx.message.role_mentions) != 1:
        await bot.say("Role not found. Make sure you enable and reference the role mention, not the name.")
        return
    log_chl = ctx.message.role_mentions[0]
    update_settings("mutedRole", log_chl.id)
    await bot.say("Muted role updated to: {}".format(log_chl.mention))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def signoff(ctx, *, target=None):
    if target is not None and len(target) > 200:
        await bot.say("Sorry, the length of your custom sign-off has to be under 200 characters.")

    update_settings("signoff", target)
    if target is None:
        await bot.say("Sign-off reset to default.")
    else:
        await bot.say("Sign-off updated to: `{}`".format(target))


@bot.command(pass_context=True)
@commands.has_permissions(manage_messages=True)
async def counter(ctx, *, target=None):
    if target is None:
        update_settings("signoff", 1)
        await bot.say("Counter reset.")
    if target.is_digit():
        update_settings("signoff", int(target))
        await bot.say("Counter set to #" + target)


if __name__ == "__main__":
    try:
        bot.run('token_here')
    except err.HTTPException:
        print("Discord seems to be experiencing some problems right now :/")
        
