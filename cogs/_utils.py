"""Utility classes used for the cogs section of this project."""

import functools
import logging
import re
from collections.abc import Callable, Coroutine, Mapping
from typing import TYPE_CHECKING, Any, Final, ParamSpec, TypeVar

import discord
from discord import Cog

from exceptions import GuildDoesNotExist, StrikeTrackingError
from utils import TeXBot

if TYPE_CHECKING:
    from typing import TypeAlias

    MentionableMember: TypeAlias = discord.Member | discord.Role | None

P = ParamSpec("P")
T = TypeVar("T")


class TeXBotAutocompleteContext(discord.AutocompleteContext):
    """
    Type-hinting class overriding AutocompleteContext's reference to the Bot class.

    Pycord's default AutocompleteContext references the standard discord.Bot class,
    but cogs require a reference to the TeXBot class, so this AutocompleteContext subclass
    should be used in cogs instead.
    """

    bot: TeXBot


class TeXBotCog(Cog):
    """Base Cog subclass that stores a reference to the currently running bot."""

    ERROR_ACTIVITIES: Final[Mapping[str, str]] = {
        "ping": "reply to ping",
        "write_roles": "send messages",
        "edit_message": "edit the message",
        "induct": "induct user",
        "silent_induct": "silently induct user",
        "non_silent_induct": "induct user and send welcome message",
        "make_member": "make you a member",
        "remind_me": "remind you",
        "channel_stats": "display channel statistics",
        "server_stats": "display whole server statistics",
        "user_stats": "display your statistics",
        "left_member_stats": (
            "display statistics about the members that have left the server"
        ),
        "archive": "archive the selected category",
        "ensure_members_inducted": "ensure all members are inducted"
    }

    def __init__(self, bot: TeXBot) -> None:
        """Initialize a new cog instance, storing a reference to the bot object."""
        self.bot: TeXBot = bot

    async def send_error(self, ctx: discord.ApplicationContext, error_code: str | None = None, message: str | None = None, logging_message: str | BaseException | None = None) -> None:  # noqa: E501
        """
        Construct & format an error message from the given details.

        The constructed error message is then sent as the response to the given
        application command context.
        """
        construct_error_message: str = ":warning:There was an error"
        construct_logging_error_message: str = ""

        if error_code:
            committee_mention: str = "committee"

            committee_role: discord.Role | None = await self.bot.committee_role
            if committee_role:
                committee_mention = committee_role.mention

            construct_error_message = (
                f"**Contact a {committee_mention} member, referencing error code:"
                f" {error_code}**\n"
                + construct_error_message
            )

            construct_logging_error_message += error_code

        command_name: str = (
            ctx.command.callback.__name__
            if (hasattr(ctx.command, "callback")
            and not ctx.command.callback.__name__.startswith("_"))
            else ctx.command.qualified_name
        )
        if command_name in self.ERROR_ACTIVITIES:
            construct_error_message += (
                f" when trying to {self.ERROR_ACTIVITIES[command_name]}"
            )

        if construct_logging_error_message:
            construct_logging_error_message += " "
        construct_logging_error_message += f"({command_name})"

        if message:
            construct_error_message += ":"
        else:
            construct_error_message += "."

        construct_error_message += ":warning:"

        if message:
            message = re.sub(
                r"<([@&#]?|(@[&#])?)\d+>", lambda match: f"`{match.group(0)}`", message.strip()
            )
            construct_error_message += f"\n`{message}`"

        await ctx.respond(construct_error_message, ephemeral=True)

        if logging_message:
            if construct_logging_error_message:
                construct_logging_error_message += " "
            logging.error("%s%s", construct_logging_error_message, logging_message)

    @staticmethod
    async def autocomplete_get_text_channels(ctx: TeXBotAutocompleteContext) -> set[discord.OptionChoice]:  # noqa: E501
        """
        Autocomplete callable that generates the set of available selectable channels.

        The list of available selectable channels is unique to each member, and is used in any
        slash-command options that have a channel input-type.
        """
        if not ctx.interaction.user:
            return set()

        try:
            guild: discord.Guild = ctx.bot.css_guild
        except GuildDoesNotExist:
            return set()

        channel_permissions_limiter: MentionableMember = await ctx.bot.guest_role
        if not channel_permissions_limiter:
            return set()

        interaction_member: discord.Member | None = guild.get_member(ctx.interaction.user.id)
        if interaction_member:
            channel_permissions_limiter = interaction_member

        if not ctx.value or re.match(r"\A#.*\Z", ctx.value):
            return {
                discord.OptionChoice(name=f"#{channel.name}", value=str(channel.id))
                for channel
                in guild.text_channels
                if channel.permissions_for(channel_permissions_limiter).is_superset(
                    discord.Permissions(send_messages=True, view_channel=True)
                )
            }

        return {
            discord.OptionChoice(name=channel.name, value=str(channel.id))
            for channel
            in guild.text_channels
            if channel.permissions_for(channel_permissions_limiter).is_superset(
                discord.Permissions(send_messages=True, view_channel=True)
            )
        }


def capture_error(func: Callable[P, Coroutine[Any, Any, T]], error_type: type[BaseException], close_func: Callable[[BaseException], None]) -> Callable[P, Coroutine[Any, Any, T | None]]:  # noqa: E501
    @functools.wraps(func)
    async def wrapper(self: TeXBotCog, /, *args: P.args, **kwargs: P.kwargs) -> T | None:
        if not isinstance(self, TeXBotCog):
            INVALID_METHOD_TYPE_MESSAGE: Final[str] = (  # type: ignore[unreachable]
                f"Parameter {self.__name__!r} of any 'capture_error' decorator"
                f" must be an instance of {TeXBotCog.__name__!r}/one of its subclasses."
            )
            raise TypeError(INVALID_METHOD_TYPE_MESSAGE)
        try:
            return await func(self, *args, **kwargs)  # type: ignore[arg-type]
        except error_type as error:
            close_func(error)
            await self.bot.close()
            return None
    return wrapper  # type: ignore[return-value]


def guild_does_not_exist_error_close_func(error: BaseException) -> None:
    logging.critical(str(error).rstrip(".:"))


def strike_tracking_error_close_func(error: BaseException) -> None:
    guild_does_not_exist_error_close_func(error)
    logging.warning("Critical errors are likely to lead to untracked moderation actions")


capture_guild_does_not_exist_error: Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T | None]]] = functools.partial(  # noqa: E501
    capture_error,  # type: ignore[arg-type]
    error_type=GuildDoesNotExist,
    close_func=guild_does_not_exist_error_close_func
)
capture_strike_tracking_error: Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T | None]]] = functools.partial(  # noqa: E501
    capture_error,  # type: ignore[arg-type]
    error_type=StrikeTrackingError,
    close_func=strike_tracking_error_close_func
)