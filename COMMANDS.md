# Exortic Selfbot Commands List

## Public Commands
These commands can be used by anyone unless the bot is `!locked`.

- `!startcount`: Starts the counting loop in the current text channel. If you are in a voice channel, the bot will join you.
- `!stopcount`: Stops the counting loop and disconnects the bot from the voice channel.
- `!join` (or `!j`): Makes the bot join your current voice channel.
- `!leave` (or `!l`): Makes the bot leave the voice channel.
- `!clear`: Deletes the bot's status messages and replies from the last 100 messages, leaving only the numbers.
- `!help`: Displays a list of all available commands.

## Owner-Only Commands
These commands can only be used by the bot owner.

- `!addadmin <@mention or ID>`: Adds a user to the admin list.
- `!removeadmin <@mention or ID>`: Removes a user from the admin list.
- `!admin`: Lists all current admins (mentions them).
- `!locked`: Restricts the bot so that only the owner can use it. Admins will be ignored.
- `!unlock`: Unlocks the bot so that admins can use commands again.

---

### Hosting Configuration
The bot requires the following environment variables to be set in Railway:
- `TOKEN`: Your Discord user token.
- `OWNER_ID`: Your Discord user ID.
