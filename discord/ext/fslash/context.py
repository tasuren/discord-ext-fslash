# discord-ext-ui - Context

from typing import Generic, Union, Optional, Any

from datetime import datetime

from discord.ext.commands.view import StringView
from discord.ext import commands
import discord

from ._types import BotT


class Context(Generic[BotT]):
    def __init__(
        self, interaction: discord.Interaction, kwargs: dict[str, Any],
        command: Optional[Union[commands.Command, commands.Group]] = None,
        bot: Optional[BotT] = None
    ):
        self.bot, self.interaction = bot, interaction

        self.message = interaction.message or self
        self.guild = interaction.guild
        self.author = interaction.user

        self.edited_at: Optional[datetime] = None
        self.created_at = interaction.created_at

        self.command, self.app_command = command, getattr(command, "__fslash__", None)
        self.args, self.kwargs = (), kwargs

        self.view = StringView("")
        self.invoked_parents = []
        self.invoked_with = None

    async def trigger_typing(self):
        ...

    async def reply(self, *args, **kwargs):
        await self.interaction.response.send_message(
            *args, **kwargs
        )


def is_fslash(context: Union[Context, commands.Context]) -> bool:
    """Checks if the specified Context is defined by fslash.

    Parameters
    ----------
    context"""
    return hasattr(context, "interaction")