# Exortic Selfbot
**Framework: Get Shit Done (GSD)**

## Project Context
The goal of this project is to develop a Discord selfbot using Python that can log into a user account, join a specified voice channel, and start counting in a specified text channel. This requires using a fork of `discord.py` that supports selfbots, such as `discord.py-self`.

## Objectives
1. Log in to a specific Discord user account using a provided user token.
2. Join a target voice channel.
3. Start a continuous counting loop in a target text channel.
4. Ensure robust error handling and smooth disconnection if needed.

## Development Roadmap
- [ ] Initialize Python environment and install `discord.py-self` and `PyNaCl` (for voice support).
- [ ] Set up the main bot script (`main.py`) to connect to Discord using the user token.
- [ ] Implement the voice channel connection logic.
- [ ] Implement the text channel message sending loop for counting.
- [ ] Test the integration locally.
