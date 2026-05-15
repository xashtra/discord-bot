import os
import discord
import asyncio
import sys

# Configuration (Set these in Railway Variables)
TOKEN = os.getenv("TOKEN")
OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else None

class SilenceSource(discord.AudioSource):
    """Sends silent audio frames to keep the voice connection alive."""
    # Opus silence frame
    SILENCE = b'\xf8\xff\xfe'

    def read(self):
        return self.SILENCE

    def is_opus(self):
        return True

class SelfBot(discord.Client):
    def __init__(self):
        # Comprehensive spoofing to match a real Windows browser
        super().__init__(
            super_properties={
                'os': 'Windows',
                'browser': 'Chrome',
                'device': '',
                'system_locale': 'en-US',
                'browser_user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'browser_version': '120.0.0.0',
                'os_version': '10',
                'referrer': '',
                'referring_domain': '',
                'referrer_current': '',
                'referring_domain_current': '',
                'release_channel': 'stable',
                'client_build_number': 302830,
                'client_event_source': None,
            }
        )
        self.counting_task = None
        self.count = 1
        self.admins = set()
        self.locked = False
        self.target_vc_channel = None  # Track VC for auto-reconnect
        self.target_text_channel = None  # Track text channel for counting
        self.keepalive_task = None

    def play_silence(self, voice_client):
        """Play silent audio to prevent idle disconnect."""
        if voice_client and voice_client.is_connected() and not voice_client.is_playing():
            voice_client.play(SilenceSource())

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        print("Ready! Join a voice channel and type !startcount in the text channel you want to count in.")
        sys.stdout.flush()
        # Start the keepalive loop
        if not self.keepalive_task:
            self.keepalive_task = self.loop.create_task(self.keepalive_loop())

    async def on_voice_state_update(self, member, before, after):
        """Auto-reconnect if the bot gets disconnected from voice."""
        if member.id != self.user.id:
            return

        # Bot was in a VC (before.channel exists) and is now disconnected (after.channel is None)
        if before.channel is not None and after.channel is None:
            if self.target_vc_channel and self.counting_task:
                print(f"Voice disconnected! Auto-reconnecting to {self.target_vc_channel.name} in 5s...")
                sys.stdout.flush()
                await asyncio.sleep(5)
                try:
                    vc = await self.target_vc_channel.connect(timeout=20.0, reconnect=True)
                    self.play_silence(vc)
                    print(f"Auto-reconnected to {self.target_vc_channel.name}")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"Auto-reconnect failed: {e}")
                    sys.stdout.flush()

    async def keepalive_loop(self):
        """Periodically check voice connection health and reconnect if needed."""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await asyncio.sleep(5 * 60)  # Check every 5 minutes

                if not self.target_vc_channel:
                    continue

                # Check if we're supposed to be in a VC but aren't
                guild = self.target_vc_channel.guild
                vc = guild.voice_client

                if vc is None or not vc.is_connected():
                    print(f"Keepalive: Not connected, reconnecting to {self.target_vc_channel.name}...")
                    sys.stdout.flush()
                    try:
                        vc = await self.target_vc_channel.connect(timeout=20.0, reconnect=True)
                        self.play_silence(vc)
                        print(f"Keepalive: Reconnected to {self.target_vc_channel.name}")
                        sys.stdout.flush()
                    except Exception as e:
                        print(f"Keepalive: Reconnect failed: {e}")
                        sys.stdout.flush()
                else:
                    # Already connected — make sure silence is playing
                    self.play_silence(vc)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Keepalive error: {e}")
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
                    
                    voice_client = await vc.connect(timeout=20.0, reconnect=True)
                    self.target_vc_channel = vc
                    self.target_text_channel = message.channel
                    self.play_silence(voice_client)
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
                self.target_vc_channel = None
                self.target_text_channel = None
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
                    voice_client = await vc_channel.connect(timeout=20.0, reconnect=True)
                    self.target_vc_channel = vc_channel
                    self.play_silence(voice_client)
                    await message.reply(f"Joined voice channel: {vc_channel.name}")
                    sys.stdout.flush()
                except Exception as e:
                    error_msg = f"Failed to join voice channel: {e}"
                    print(error_msg)
                    await message.reply(error_msg)
                    sys.stdout.flush()
            else:
                await message.reply("You are not in a voice channel. Please join one first.")

        elif content.startswith("!leave") or content.startswith("!l"):
            self.target_vc_channel = None
            disconnected = False
            for vc in self.voice_clients:
                await vc.disconnect()
                disconnected = True
            
            if disconnected:
                await message.reply("Left the voice channel.")
            else:
                await message.reply("I am not in a voice channel.")

        elif content.startswith("!countclear"):
            try:
                num = int(content.split()[1])
            except (IndexError, ValueError):
                await message.reply("Usage: !countclear <number>")
                return

            deleted = 0
            try:
                async for msg in message.channel.history(limit=500):
                    if deleted >= num:
                        break
                    # Only delete the bot's counting messages (digits only)
                    if msg.author.id == self.user.id and msg.content.isdigit():
                        await msg.delete()
                        deleted += 1
                        await asyncio.sleep(1)  # Avoid rate limits

                # Roll back the count
                self.count = max(1, self.count - deleted)
                await message.reply(f"Deleted {deleted} counting messages. Count reset to {self.count}.")
            except Exception as e:
                print(f"Error during countclear: {e}")
                sys.stdout.flush()
                await message.reply(f"Error: {e}")

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
                "- `!countclear <number>`: Delete the latest N counting messages.\n"
                "- `!help`: Show this list.\n\n"
                "**Owner Only:**\n"
                "- `!addadmin <@mention/ID>`: Add an admin.\n"
                "- `!removeadmin <@mention/ID>`: Remove an admin.\n"
                "- `!admin`: Show current admins.\n"
                "- `!locked`: Restrict to owner only.\n"
                "- `!unlock`: Allow admins again."
            )
            await message.reply(help_text)


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
