# AnonMsg
A Discord Bot that sends messages, anonymously and with approval.

Uses the v0.16.12 fork of the Discord.py Library. [Click Here](https://discordpy.readthedocs.io/en/v0.16.12/index.html) for the documentation.

Features:
- Anonymous messaging in a specific channel
- Moderator approval/notification system using reactions
- Support for newlines, code blocks and standard Discord emoji

Commands:

<b>anon.info</b> - Returns uptime, user/server reach, and the output/notification channels.

<b>anon.send [message]</b> - Sends an anonymous message off for review. Only functional in a DM with the bot.

<b>anon.review</b> - [Mod Only] Starts the approval queue, where you can react to allow/deny messages.

<b>anon.output</b> - [Mod Only] Sets the channel you want approved anonymous messages to be sent.

<b>anon.notif</b> - [Mod Only] Sets the channel you want to send the approval notification.
