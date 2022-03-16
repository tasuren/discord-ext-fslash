# discord-ext-fslash

from discord.ext import commands
import discord

from discord.ext.commands._types import BotT


class DiscordExtFSlash(commands.Cog):
    def __init__(self, bot: BotT):
        self.bot = bot

    async def process_interaction(self, interaction: discord.Interaction):
        ...


async def setup(bot):
    return await bot.add_cog(DiscordExtFSlash(bot))