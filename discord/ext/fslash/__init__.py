".. include:: ../../../README.md" # discord-ext-fslash

from __future__ import annotations

from typing import Callable, Iterable, Literal, Union, Optional, Any, DefaultDict

from inspect import isfunction, iscoroutinefunction
from collections import defaultdict
from string import octdigits
from re import sub
import inspect

from discord.ext import commands
from discord import app_commands
import discord

from ._types import AdjustmentNameMode, BotT, TriggerTypingMode, InteractionResponseMode
from .context import Context, is_fslash


__all__ = (
    "extend_force_slash", "is_fslash", "Context", "AdjustmentNameMode",
    "groups", "exceptions", "adjustment_command_name", "TriggerTypingMode",
    "InteractionResponseMode"
)
__version__ = "0.1.10"
__author__ = "tasuren"


VALID_COMMAND_NAME_CHARACTERS_WITHOUT_LETTERS = f"{octdigits}-_"
def adjustment_command_name(name: str, mode: AdjustmentNameMode) -> str:
    """Prepares the passed string into a string that can be used as the name of a slash command.

    Parameters
    ----------
    name : str
        Adjustment target.
    mode : AdjustmentNameMode
        It is either a snake case or a kebab case."""
    sandwiched = "_" if mode == AdjustmentNameMode.SNAKE_CASE else "-"
    return "".join(
        char
        for char in sub(
            "(.[A-Z])", lambda x: f"{x.group(1)[0]}{sandwiched}{x.group(1)[1]}", name.lower()
        ).lower()
        if char in VALID_COMMAND_NAME_CHARACTERS_WITHOUT_LETTERS
    )[:32]


_bot = None
_context_kwargs = {}


# ConverterのアノテーションをTransformerに交換するようにする。
_original_evaluate_annotation = discord.utils.evaluate_annotation
def _new_evaluate_annotation(*args, **kwargs):
    annotation = _original_evaluate_annotation(*args, **kwargs)
    if commands.Converter in getattr(annotation, "__mro__", ()):
        converter = annotation()
        # Converterを実行するTransformerを作る。
        class ConverterTransformer(app_commands.Transformer):

            # コマンドフレームワークで実行された際には、元のコンバーターを実行できるように元を取って置く。
            __fslash_original_annotation__ = annotation

            @classmethod
            async def transform(cls, interaction, value: str):
                return await converter.convert(
                    Context(interaction, {}, None, _bot, **_context_kwargs), value
                )
        annotation = app_commands.Transform[None, ConverterTransformer]
    if isfunction(annotation):
        # 関数のコンバーターを実行するTransformerを作る。
        converter = annotation
        class ConverterTransformer(app_commands.Transformer):

            __fslash_original_annotation__ = annotation

            @classmethod
            async def transform(cls, _, value):
                return await converter(value) if iscoroutinefunction(converter) else converter(value)
        annotation = app_commands.Transform[None, ConverterTransformer]
    return annotation
discord.utils.evaluate_annotation = _new_evaluate_annotation


_original_atp = app_commands.transformers.annotation_to_parameter
_original_signature = inspect.signature
def _replace_atp(toggle: bool, failed_annotations: Optional[dict] = None, riats: bool = False):
    # `annotation_to_parameter`の実行が失敗した際に`str`として扱うようにする関数です。
    # それと、inspectの`signature`もアノテーションがない場合は拡張します。
    if toggle:
        def new_atp(annotation, parameter):
            if riats:
                try:
                    return _original_atp(annotation, parameter)
                except Exception as e:
                    # 失敗したなら`str`のアノテーションにする。
                    if failed_annotations is not None:
                        failed_annotations[str(annotation)] = e
                    if parameter.kind in (
                        parameter.POSITIONAL_ONLY, parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL
                    ):
                        parameter = parameter.replace(kind=parameter.KEYWORD_ONLY)
                    return _original_atp(str, parameter)
            else:
                return _original_atp(annotation, parameter)
        app_commands.transformers.annotation_to_parameter = new_atp
        app_commands.commands.annotation_to_parameter = new_atp

        def new_signature(*args, **kwargs):
            signature = _original_signature(*args, **kwargs)
            ok = False
            new = []
            for name, parameter in list(signature.parameters.items()):
                if name == "ctx":
                    ok = True
                new.append(parameter)
                if ok and parameter.annotation == parameter.empty:
                    # アノテーションがない場合は`str`を設定して置く。
                    new[-1] = parameter.replace(annotation=str)
            return signature.replace(parameters=new) if ok else signature
        inspect.signature = new_signature
    else:
        app_commands.transformers.annotation_to_parameter = _original_atp
        app_commands.commands.annotation_to_parameter = _original_atp
        inspect.signature = _original_signature


def _get(command, key, default):
    # コマンドオブジェクトの`__original_kwargs__`か`extras`から特定の値を取り出します。
    return command.__original_kwargs__.get(key, default) \
        or command.extras.get(key, default)


# `parse_arguments`で何も実行しないようにする。
_original_parse_arguments = commands.Command._parse_arguments
async def _new_parse_arguments(self, ctx):
    if is_fslash(ctx) and not getattr(ctx, "__fslash_do_original_pa__", False):
        ctx.args = (ctx.command.cog, ctx) if ctx.command.cog else (ctx,)
    else:
        return await _original_parse_arguments(self, ctx)
setattr(commands.Command, "_parse_arguments", _new_parse_arguments)


async def _run_command(bot, interaction, command, content, kwargs={}) -> None:
    # Run command
    ctx = Context(interaction, kwargs, command, bot, **_context_kwargs)
    if content is not None:
        ctx.view = type(ctx.view)(content)
        setattr(ctx, "__fslash_do_original_pa__", True)
    try:
        await command.invoke(ctx) # type: ignore
    except commands.CommandError as e:
        await command.dispatch_error(ctx, e)
    else:
        bot.dispatch("command_completion", ctx)


def _apply_describe(command):
    # `describe`等で付けられたデータを`callback`にも適用させる。
    for name, value in filter(
        lambda x: x[0].startswith("__discord_app_commands"),
        command.__dict__.items()
    ):
        setattr(command.callback, name, value)


_original_run_converter = commands.core.run_converters # type: ignore
async def _new_run_converters(ctx, converter, argument, param):
    origin = getattr(converter, "__origin__", None)
    is_choice = False
    if origin is app_commands.Choice and hasattr(
        ctx.command.callback, "__fslash_param_choices__"
    ):
        # ChoiceをLiteralに交換する。
        if choices := ctx.command.callback.__fslash_param_choices__.get(param.name):
            converter = Literal[0]
            setattr(converter, "__args__", tuple(choice.name for choice in choices))
            is_choice = True
    elif isinstance(converter, app_commands.transformers._TransformMetadata):
        # TransformはConverterに置き換える。
        converter = getattr(converter.metadata, "__fslash_original_annotation__")
    data = await _original_run_converter(ctx, converter, argument, param)
    if is_choice:
        data = discord.utils.get(choices, name=data)
    return data
commands.core.run_converters = _new_run_converters # type: ignore


groups = []
"List containing group commands scheduled to be registered with a slash."
exceptions: DefaultDict[str, dict[Any, Exception]] = defaultdict(dict)
"This dictionary is used to include errors when something failed but did not output an error."
__patched = False
def extend_force_slash(
    bot: BotT, *,
    check: Optional[Callable[[Union[commands.Command, commands.Group]], bool]] = None,
    adjustment_name: Optional[AdjustmentNameMode] = None,
    replace_invalid_annotation_to_str: bool = False,
    default_description: str = "...", first_groups: Optional[Iterable[app_commands.Group]] = None,
    context_kwargs: Optional[dict] = None
) -> BotT:
    """This class forces commands in the command framework bot to be registered even if they are slash commands.

    Parameters
    ----------
    bot : discord.ext.commands.bot.Bot
        Target Bot.
    check : Callable[[Union[commands.Command, commands.Group]], bool], optional
        Function used to check if a command should be added.  
        This is useful if you do not want some commands to be registered as slashes.
    adjustment_name : AdjustmentNameMode, optional
        Whether the name should be Snake Case or Kebab Case and the number of characters should be automatically converted to 32 or less.  
        If you have many commands with names that cannot be used as slash command names, this is useful because it will automatically convert them all to usable names.
    replace_invalid_annotation_to_str : bool, default False
        Whether invalid annotations as slashes are automatically set to `str`.  
        The default is `False`, but if you have a lot of commands and are not confident that all the annotations are correct and do not have the energy to fix the wrong ones, you can use this.  
        When automatically exchanged for `str`, the error is written to `fslash.exceptions["annotation"]`.  
        If you think something is wrong, check here.
    default_description : str, default "..."
        This is the string to put in place when an empty description is encountered.
    first_groups : Iterable[discord.app_commands.Group], optional
        This is a list of group commands to be registered first.  
        If you have reached the maximum number of slash commands that can be registered, you can register more commands by registering the already registered commands as subcommands of the group command in this list.  
        How to do it is described in the Notes of this function.
    context_kwargs : dict, optional
        Keyword arguments to be passed to the arguments after `trigger_typing_mode` of `fslash.context.Context`.  
        Detail is here: `Context`

    Warnings
    --------
    This function performs a monkey patch so that the command framework command is registered as a slash at runtime.  
    It also temporarily replaces the command framework command object and the `signature` of the standard library `inspect` with another one.  
    We will try to avoid interfering with other libraries as much as possible, but we can't guarantee that we won't, so please understand that and use it accordingly.  
    And you can only call this function once.

    Notes
    -----
    One may wonder if decorators such as `app_commands.describe` can be used, but of course they can.  
    Also, the command framework checks work.  
    The converter is automatically replaced by `app_commands.Transformer`.  
    Cooldown also works.  
    However, the decorator must be placed below `command`.  
    If you have a lot of nested commands like group command of group command of group command... you can't register them in the slash as they should be.  
    If such a command is encountered, it will take the subcommands after the unregistrable subcommand as arguments.  
    Example: `/group level1 level2 content: level3 level4 ...`

    The number of slash commands registered may exceed the maximum number of slash commands registered as commands in the command framework.  
    In that case, use the `first_groups` argument.  
    The command in the list of group commands passed to this argument can be set as the parent command of the command framework command.  
    To do this, simply enter the name of the parent command as `fsparent` in the command framework command argument or `extras` argument.  
    Example:  
    ```python
    bot = extend_force_slash(
        commands.Bot(command_prefix="t!", intents=intents),
        first_groups=(
            discord.app_commands.Group(
                name="server-tool", description="Some commands are useful for server operation."
            ),
        )
    )


    @bot.command(fsparent="server-tool") # or `extras={"fsparent": "server-tool"}`
    async def normal(ctx):
        "This command can be called by run `/server-tool normal`."
    ```

    You can also specify a guild.  
    Just pass a value for the `guild` argument, similar to `guild` in `CommandTree.command`.  
    (Or you can pass `guild` as a key to `extras`).  
    Group commands can also be passed in the same way as `app_commands.Group`. (`guild_ids`)  
    ```python
    @bot.command(guild=GUILD_ID)
    async def test(ctx):
        ...
    ```

    You can change which methods return interaction responses and how `Context.trigger_typing` behaves by passing a value to `Context` with the `context_kwargs` argument.
    Also, `discord.app_commands.Choice` is replaced by `Literal` in the command framework commands.  
    But the value of the argument at runtime is the value of `Choice`."""
    global _bot, groups, exceptions, _context_kwargs
    _context_kwargs.update(context_kwargs or {})
    _bot = bot
    if first_groups is not None:
        for g in first_groups:
            groups.append(g)

    global __patched
    assert not __patched, "This can only be called once."
    __patched = True
    if check is None: check = lambda _: True

    # コマンドが作られた際にそのコマンドを呼び出すコマンドをtreeに登録する。
    original_command_init = commands.Command.__init__
    def command_new_init(command: commands.Command, func, /, **kwargs):
        if not (cog_mode := kwargs.pop("__cog_mode__", False)):
            original_command_init(command, func, **kwargs)

        # コグに実装されているコマンドの場合はコグが追加された後にスラッシュとして登録する。
        # 理由は内部でコピーを行うためここが(多分)二回呼ばれてしまうためで、それを対策しようとするととてもめんどくさいことになってしまうから。
        if command.callback.__code__.co_varnames[0] == "self" and not cog_mode:
            if not isinstance(command, commands.Group):
                _apply_describe(command)
            return

        # もしNestしすぎたグループコマンドのコマンドの場合はパスする。この`__fslash_*_*__`は下で作られます。
        if command.parent is not None and getattr(
            command.parent, "__fslash_max_parent__", False
        ):
            setattr(command, "__fslash_max_parent__", True)
            return

        # コマンドを実装するかのチェックをする。
        if not check(command): return

        _replace_atp(
            True, exceptions["replace_invalid_annotation_to_str"],
            replace_invalid_annotation_to_str
        )

        # もし親のグループが指定されているのならそれを探し出す。
        parent = None
        fsparent = _get(command, "fsparent", None)
        for group in groups:
            if fsparent == group.name:
                parent = group
                break
        else:
            assert fsparent is None, f"A group command that has not yet been registered as a parent command in `{command}` has been specified."
        # もしコマンドフレームワークのグループコマンドのサブコマンドの場合は、親コマンドのスラッシュのグループコマンドを、スラッシュでも親コマンドとする。
        if parent is None and command.parent is not None:
            parent = getattr(command.parent, "__fslash__", None)
            if parent is None:
                return _replace_atp(False, None, replace_invalid_annotation_to_str)
        # choiceのデータをコマンドフレームワークのコマンド実行時にLiteralに交換するので取って置く。
        if hasattr(command.callback, "__discord_app_commands_param_choices__"):
            setattr(
                command._callback, "__fslash_param_choices__",
                getattr(
                    command.callback, "__discord_app_commands_param_choices__", None
                ).copy() # type: ignore
            )
        # スラッシュコマンドを作る。
        name = command.name if adjustment_name is None \
            else adjustment_command_name(command.name, adjustment_name)
        if getattr(parent, "__fslash_max_parent__", False):
            return _replace_atp(False, None, replace_invalid_annotation_to_str)
        try:
            assert parent is None or len(parent._children) < 24
            if isinstance(command, commands.Group):
                groups.append(app_commands.Group(
                    name=name,
                    description=command.description or default_description,
                    parent=parent, guild_ids=_get(command, "guild_ids", None)
                ))
                setattr(command, "__fslash__", groups[-1])
            else:
                _apply_describe(command)
                # スラッシュコマンドを作る。
                app_command: app_commands.Command = (bot.tree.command if parent is None else parent.command)(
                    name=name, description=command.description or default_description,
                    **(dict(
                        guild=_get(command, "guild", discord.utils.MISSING), guilds=_get(
                            command, "guilds", discord.utils.MISSING
                        )
                    ) if parent is None else {})
                )(command.callback) # type: ignore
                setattr(command, "__fslash__", app_command)

                # 実行される関数を用意する。
                async def inner_function(interaction: discord.Interaction, **kwargs): # type: ignore
                    await _run_command(bot, interaction, command, None, kwargs)
                setattr(app_command, "_callback", inner_function)
        except (ValueError, AssertionError) as e:
            # もしNestしすぎたグループコマンドがある場合は、コマンドの文を受け取るコマンドを代わりに作る。
            assert isinstance(parent, app_commands.Group)
            @parent.command(
                name=name, description=command.description or default_description
            )
            async def alternative_for_nested(
                interaction: discord.Interaction, content: str
            ):
                await _run_command(bot, interaction, command, content)
            setattr(command, "__fslash_max_parent__", True)
            if isinstance(e, AssertionError):
                setattr(parent, "__fslash_max_parent__", True)

        _replace_atp(False, None, replace_invalid_annotation_to_str)
    setattr(commands.Command, "__init__", command_new_init)

    # コグ追加時に、コグに実装されているコマンドをスラッシュで登録する。
    original_inject = commands.Cog._inject
    def new_inject(self: commands.Cog, *args, **kwargs):
        for command in self.__cog_commands__:
            command_new_init(command, command.callback, __cog_mode__=True)
        return original_inject(self, *args, **kwargs)
    commands.Cog._inject = new_inject

    # コマンドが削除された時はスラッシュコマンドも削除する。
    def command_new_del(command: commands.Command):
        slash: Optional[app_commands.Command] = getattr(command, "__fslash__", None);
        if slash is not None:
            if slash.parent is None:
                bot.tree.remove_command(slash) # type: ignore
            else:
                slash.parent.remove_command(slash) # type: ignore
    setattr(commands.Command, "__del__", command_new_del)

    # `sync`が実行された際に`groups`にあるものを追加するようにする。
    original_sync = app_commands.CommandTree.sync
    async def new_sync(self, *, guild=None):
        for group in groups:
            if not getattr(group, "__synced__", False) \
                    and group.parent is None:
                bot.tree.add_command(group)
                setattr(group, "__synced__", True)
        return await original_sync(self, guild=guild)
    app_commands.CommandTree.sync = new_sync

    return bot
