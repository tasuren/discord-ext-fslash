# discord-ext-fslash - Context

from __future__ import annotations

from typing import Generic, Union, Optional, Any

from datetime import datetime

from discord.ext.commands.view import StringView
from discord.ext import commands
import discord

from .types_ import BotT, TypingMode, InteractionResponseMode


class NewTyping:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    async def __aenter__(self):
        if self.ctx.typing_mode == TypingMode.TYPING: # type: ignore
            await super().__aenter__()
        else:
            if self.typing_mode == TypingMode.TYPING:
                await self.channel.typing() # type: ignore
            elif self.typing_mode.name.startswith("DEFER"):
                await self.interaction.response.defer(
                    ephemeral=self.typing_mode.name.endswith("EPHEMERAL"),
                    thinking="THINKING" in self.typing_mode.name
                )
                self._sended_defer = True

    async def __aexit__(self, *_):
        ...

    def __await__(self):
        return self.__aenter__().__await__()


class Context(Generic[BotT]):
    """Context that is passed to the command framework commands at slash execution time instead.

    Warnings
    --------
    This is different from the usual `discord.ext.commands.Context`.  
    We have tried to make it as similar to the original Context as possible, but some of the commands in the command framework may behave unexpectedly.  
    It is recommended to check just in case.

    Note
    ----
    The following are attributes that are guaranteed to work.

    * bot
    * guild
    * author
    * channel
    * cog
    * me
    * voice_client
    * send
    * reply
    * typing
    * history
    * pins
    * fetch_message
    * add_reaction (Do nothing)
    * remove_reaction (Do nothing)

    `send_help` is currently not implemented.

    Parameters
    ----------
    interaction : discord.Interaction
    kwargs : dict[str, Any]
    command : Union[discord.ext.commands.Command, discord.ext.commands.Group], optional
    bot : discord.ext.commands.Bot, optional
    interaction_response_mode : types_.InteractionResponseMode, default types._InteractionResponseMode.REPLY
        Which method is used to reply to the interaction response.
    typing_mode : types_.TypingMode, default types_.TypingMode.DEFER_THINKING
        Sets the behavior when `Context.typing` and `Context.typing` is executed.  
        You can use `defer` in the interaction response instead.  
        The `Context.reply` can still be used afterwards."""

    __fslash__ = True

    def __init__(
        self, interaction: discord.Interaction, kwargs: dict[str, Any],
        command: Optional[Union[commands.Command, commands.Group]] = None,
        bot: Optional[BotT] = None,
        interaction_response_mode: InteractionResponseMode = InteractionResponseMode.REPLY,
        typing_mode: TypingMode = TypingMode.DEFER_THINKING
    ):
        self.bot, self.interaction, self._state = bot, interaction, bot._connection

        self.message = interaction.message or self
        self.mentions = []
        self.guild = interaction.guild
        self.author = interaction.user
        self.channel = interaction.channel or interaction.user
        self.fetch_message = self.channel.fetch_message # type: ignore
        self.history = self.channel.history # type: ignore
        self.pins = self.channel.pins # type: ignore
        if self.guild is None:
            self.me, self.voice_client = None, None
        else:
            self.me = self.guild.me
            self.voice_client = self.guild.voice_client

        self.valid = True
        self.prefix = "/"
        self.clean_prefix = "/"
        self.cog = None if command is None else command.cog
        self.command_failed = False
        self.subcommand_passed = None
        self.invoked_subcommand = None

        self.edited_at: Optional[datetime] = None
        self.created_at = interaction.created_at

        self.command, self.app_command = command, getattr(command, "__fslash__", None)
        self.args, self.kwargs = (), kwargs

        if self.command is None:
            self.reinvoke, self.invoke = None, None
        else:
            self.reinvoke = self.command.reinvoke

        self.view = StringView("")
        self.invoked_parents: list[Any] = []
        self.invoked_with = None
        self.edit = self._reply
        self.attachments = []

        self.typing_mode = typing_mode
        self.interaction_response_mode = interaction_response_mode
        self._sended_defer = False
        self._emojis = ""

    async def invoke(self, command, *args, **kwargs):
        return await command(self, *args, **kwargs)

    async def _reply(self, content, kwargs):
        if self._sended_defer:
            if content is not None:
                kwargs["content"] = content
            await self.interaction.edit_original_response(**kwargs)
            return self
        else:
            return await self.interaction.response.send_message(
                content, **kwargs
            )

    async def reply(self, content: Optional[str] = None, **kwargs):
        if self.interaction_response_mode in (
            InteractionResponseMode.REPLY, InteractionResponseMode.SEND_AND_REPLY
        ):
            return await self._reply(content, kwargs)

    async def send(self, content: Optional[str] = None, **kwargs):
        if self.interaction_response_mode in (
            InteractionResponseMode.SEND, InteractionResponseMode.SEND_AND_REPLY
        ):
            await self._reply(content, kwargs)
            return self
        else:
            return await self.channel.send(content, **kwargs) # type: ignore

    def typing(self) -> NewTyping:
        return NewTyping(self) # type: ignore

    async def add_reaction(self, _): ...

    async def remove_reaction(self, _, __): ...


def is_fslash(context: Union[Context, commands.Context]) -> bool:
    """Checks if the specified Context is defined by fslash.

    Parameters
    ----------
    context"""
    return getattr(context, "__fslash__", False)