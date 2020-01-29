# AnonMsg
A Discord Bot that sends messages, anonymously and with approval.

Uses the v0.16.12 fork of the Discord.py Library. [Click Here](https://discordpy.readthedocs.io/en/v0.16.12/index.html) for the documentation. (I'm currently working on migrating this to the most recent version)

Features:
- Anonymous messaging in a specific channel
- Moderator approval/notification system using reactions
- Support for newlines, code blocks and standard Discord emoji

Commands:

<b>anon.info</b> - Returns uptime, user/server reach, and the output/notification channels.

<b>anon.send [message]</b> - Sends an anonymous message off for review. Only functional in a DM with the bot.

<b>anon.review</b> - Starts the approval queue, where you can react to allow/deny messages. (Mod Only)

<b>anon.output {channel mention}</b> - Sets the channel you want approved anonymous messages to be sent. (Mod Only)

<b>anon.notif {channel mention}</b> - Sets the channel you want to send the approval notification. (Mod Only)

<b>anon.mutedrole {role mention}</b> - When the message sender has this role, it will not be submitted. (Mod Only)

<b>anon.signoff {message}</b> - Customise signoff at the end of each message. Leave blank for a random selection. (Mod Only)

<b>anon.counter {number}</b> - Reset or set the message counter to a specific number. (Mod Only)
