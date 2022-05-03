# discord-ext-fslash - Types

from typing import TypeVar
from enum import Enum


__all__ = ("AdjustmentNameMode", "TriggerTypingMode", "InteractionResponseMode", "ContextMode")


class AdjustmentNameMode(Enum):
    "It is how lib arrange the name."

    SNAKE_CASE = 1
    KEBAB_CASE = 2


class TriggerTypingMode(Enum):
    "The type of :meth:``fslash.context.Context.trigger_typing`` to identify its behavior."

    "Do nothing."
    NOTHING = 0
    TYPING = 1
    DEFER = 2
    DEFER_EPHEMERAL = 3
    DEFER_THINKING = 4
    DEFER_THINKING_EPHEMERAL = 5


class InteractionResponseMode(Enum):
    "What method is used to return the response of the interaction."

    REPLY = 0
    SEND = 1
    SEND_AND_REPLY = 2
    "Nothing, only ``interaction.response``."
    NONE = 3


class ContextMode(Enum):
    "It is how to create Context."

    OFFICIAL = 0
    "Use the standard `Context.from_interaction` in discord.py."
    UNOFFICIAL = 1
    "Use the `Context` provided in `discord-ext-fslash`."


BotT = TypeVar("BotT")