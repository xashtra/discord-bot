import os
import discord
import asyncio
import sys

# Configuration (Set these in Railway Variables)
TOKEN = os.getenv("TOKEN")
OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else None

class SelfBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.counting_task = None
        self.count = 1
        self.admins = set()
        self.locked = False

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        print("Ready! Join a voice channel and type !startcount in the text channel you want to count in.")
        sys.stdout.flush()

    async def on_message(self, message):
        # Determine roles
        is_owner = (message.author.id == OWNER_ID or message.author.id == self.user.id)
        is_admin = (message.author.id in self.admins)

        # Permission check
        if not is_owner:
            if self.locked or not is_admin:
                return

        content = message.content.strip()

        if message.content.startswith("!startcount"):
            if self.counting_task:
                await message.reply("Already counting!")
                return

            if message.author.voice and message.author.voice.channel:
                vc = message.author.voice.channel
                try:
                    # Disconnect from any existing voice clients first
                    for existing_vc in self.voice_clients:
                        await existing_vc.disconnect()
                    
                    await vc.connect()
                    await message.reply(f"Joined voice channel: {vc.name}")
                    sys.stdout.flush()
                except Exception as e:
                    await message.reply(f"Failed to join voice channel: {e}")
                    sys.stdout.flush()
                    return
            else:
                await message.reply("You are not in a voice channel. Please join one first. Note: Selfbots sometimes take a moment to see your voice state. If you are in a VC, try re-joining it, then run the command.")
                return

            self.counting_task = self.loop.create_task(self.count_loop(message.channel))
            await message.reply(f"Counting started in {message.channel.name}")

        elif content.startswith("!stopcount"):
            if self.counting_task:
                self.counting_task.cancel()
                self.counting_task = None
                await message.reply("Stopped counting.")
                for vc in self.voice_clients:
                    await vc.disconnect()
            else:
                await message.reply("Not currently counting.")

        elif content.startswith("!join") or content.startswith("!j"):
            if message.author.voice and message.author.voice.channel:
                vc_channel = message.author.voice.channel
                try:
                    # Disconnect existing first
                    for vc in self.voice_clients:
                        if vc.guild.id == message.guild.id:
                            await vc.disconnect()
                    
                    print(f"Attempting to join {vc_channel.name}...")
                    await vc_channel.connect(timeout=20.0, reconnect=True)
                    await message.reply(f"Joined voice channel: {vc_channel.name}")
                    sys.stdout.flush()
                except Exception as e:
                    error_msg = f"Failed to join voice channel: {e}"
                    print(error_msg)
                    await message.reply(error_msg)
                    sys.stdout.flush()
            else:
                await message.reply("You are not in a voice channel. Please join one first.")

        elif message.content.startswith("!leave") or message.content.startswith("!l"):
            disconnected = False
            for vc in self.voice_clients:
                await vc.disconnect()
                disconnected = True
            
            if disconnected:
                await message.reply("Left the voice channel.")
            else:
                await message.reply("I am not in a voice channel.")

        elif message.content.startswith("!clear"):
            await message.reply("Clearing messages...")
            # Delete messages sent by the selfbot that are NOT numbers (like replies/status msgs)
            try:
                count = 0
                async for msg in message.channel.history(limit=100):
                    # If it's a message from the selfbot
                    if msg.author.id == self.user.id:
                        # Don't delete numbers (the counting messages)
                        if not msg.content.isdigit():
                            await msg.delete()
                            count += 1
                            await asyncio.sleep(1) # sleep to avoid rate limits on deletion
                
                # We will also delete the `!clear` command if the owner sent it
                if message.author.id == OWNER_ID:
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass # Cannot delete owner's message if no perm, though selfbots can only delete own msgs usually, we'll try
                        
            except Exception as e:
                print(f"Error during clearing: {e}")
                sys.stdout.flush()

        elif content == "!help":
            help_text = (
                "**Exortic Selfbot Commands:**\n"
                "- `!startcount`: Start counting in the current channel.\n"
                "- `!stopcount`: Stop counting and leave VC.\n"
                "- `!join` / `!j`: Join your current voice channel.\n"
                "- `!leave` / `!l`: Leave the voice channel.\n"
                "- `!clear`: Delete the bot's non-number messages.\n"
                "- `!help`: Show this list.\n\n"
                "**Owner Only:**\n"
                "- `!addadmin <@mention/ID>`: Add an admin.\n"
                "- `!removeadmin <@mention/ID>`: Remove an admin.\n"
                "- `!admin`: Show current admins.\n"
                "- `!locked`: Restrict to owner only.\n"
                "- `!unlock`: Allow admins again."
            )
            await message.reply(help_text)

        elif content == "!stopcount":
            if self.counting_task:
                self.counting_task.cancel()
                self.counting_task = None
                await message.reply("Stopped counting and leaving voice.")
                for vc in self.voice_clients:
                    await vc.disconnect()
            else:
                await message.reply("Not currently counting.")

        # Owner-only Admin/Lock commands
        elif is_owner:
            if content.startswith("!addadmin"):
                try:
                    # Handle mentions like <@123456789> or <@!123456789>
                    raw_id = content.split()[1].strip('<@!>')
                    admin_id = int(raw_id)
                    self.admins.add(admin_id)
                    await message.reply(f"Added {admin_id} to admin list.")
                except (IndexError, ValueError):
                    await message.reply("Usage: !addadmin <ID or @mention>")

            elif content.startswith("!removeadmin"):
                try:
                    raw_id = content.split()[1].strip('<@!>')
                    admin_id = int(raw_id)
                    if admin_id in self.admins:
                        self.admins.remove(admin_id)
                        await message.reply(f"Removed {admin_id} from admin list.")
                    else:
                        await message.reply(f"{admin_id} is not an admin.")
                except (IndexError, ValueError):
                    await message.reply("Usage: !removeadmin <ID or @mention>")

            elif content.startswith("!locked"):
                self.locked = True
                await message.reply("Bot is now LOCKED to owner only.")

            elif content.startswith("!unlock"):
                self.locked = False
                await message.reply("Bot is now UNLOCKED for admins.")

            elif content == "!admin":
                if not self.admins:
                    await message.reply("No admins added.")
                else:
                    mentions = [f"<@{admin_id}>" for admin_id in self.admins]
                    await message.reply(f"**Current Admins:** {' '.join(mentions)}")

    async def count_loop(self, channel):
        while True:
            try:
                await channel.send(str(self.count))
                self.count += 1
                # Sleep for 4 minutes
                await asyncio.sleep(4 * 60)  
            except Exception as e:
                print(f"Error while counting: {e}")
                sys.stdout.flush()
                await asyncio.sleep(4 * 60)

if __name__ == "__main__":
    if not TOKEN or not OWNER_ID:
        print("ERROR: TOKEN or OWNER_ID environment variables are missing!")
        sys.exit(1)
    bot = SelfBot()
    bot.run(TOKEN)
