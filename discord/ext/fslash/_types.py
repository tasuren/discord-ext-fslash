# discord-ext-fslash - Types

from typing import TypeVar
from enum import Enum

from discord.ext.commands.bot import BotBase


class AdjustmentNameMode(Enum):
    SNAKE_CASE = 1
    KEBAB_CASE = 2


BotT = TypeVar("BotT", bound=BotBase)