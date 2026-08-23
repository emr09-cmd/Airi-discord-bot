# ticket.py

import discord
from discord.ui import View


# ============================================================
# CONFIG
# ============================================================

TICKET_CATEGORY_ID = 0

TICKET_LOG_CHANNEL_ID = 0

STAFF_ROLE_ID = 0


# ============================================================
# HELPERS
# ============================================================

def get_ticket_category(guild):

    if TICKET_CATEGORY_ID == 0:
        return None

    channel = guild.get_channel(
        TICKET_CATEGORY_ID
    )

    if isinstance(
        channel,
        discord.CategoryChannel
    ):
        return channel

    return None


def get_staff_role(guild):

    if STAFF_ROLE_ID == 0:
        return None

    return guild.get_role(
        STAFF_ROLE_ID
    )


async def log_ticket(
    guild,
    text
):

    if TICKET_LOG_CHANNEL_ID == 0:
        return

    channel = guild.get_channel(
        TICKET_LOG_CHANNEL_ID
    )

    if channel is None:

        try:

            channel = await guild.fetch_channel(
                TICKET_LOG_CHANNEL_ID
            )

        except Exception as e:

            print(
                f"[TICKET] Log channel error: {e}"
            )

            return

    try:

        await channel.send(text)

    except Exception as e:

        print(
            f"[TICKET] Log error: {e}"
        )


# ============================================================
# CLOSE CONFIRMATION
# ============================================================

class CloseConfirmView(View):

    def __init__(self):

        super().__init__(
            timeout=30
        )

    @discord.ui.button(
        label="Confirm Close",
        style=discord.ButtonStyle.danger,
        emoji="🔒"
    )
    async def confirm_close(
        self,
        interaction,
        button
    ):

        channel = interaction.channel

        if channel is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        print(
            f"[TICKET] Closing {channel.name}"
        )

        if interaction.guild:

            await log_ticket(
                interaction.guild,
                (
                    f"🔒 `{channel.name}` "
                    f"closed by "
                    f"{interaction.user.mention}"
                )
            )

        try:

            await channel.delete(
                reason=(
                    f"Ticket closed by "
                    f"{interaction.user}"
                )
            )

        except Exception as e:

            print(
                f"[TICKET] Delete error: {e}"
            )


    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌"
    )
    async def cancel_close(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content="Ticket close cancelled.",
            view=None
        )


# ============================================================
# TICKET CONTROL
# ============================================================

class TicketControlView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket:close"
    )
    async def close_ticket(
        self,
        interaction,
        button
    ):

        print(
            f"[TICKET] Close button clicked by "
            f"{interaction.user}"
        )

        channel = interaction.channel
        guild = interaction.guild

        if channel is None or guild is None:
            return

        allowed = False

        # Ticket owner.
        if channel.topic:

            prefix = "ticket_owner:"

            if channel.topic.startswith(prefix):

                try:

                    owner_id = int(
                        channel.topic[len(prefix):]
                    )

                    if interaction.user.id == owner_id:
                        allowed = True

                except ValueError:
                    pass

        # Staff.
        staff_role = get_staff_role(
            guild
        )

        if (
            staff_role is not None
            and isinstance(
                interaction.user,
                discord.Member
            )
            and staff_role in interaction.user.roles
        ):
            allowed = True

        # Administrator.
        if (
            isinstance(
                interaction.user,
                discord.Member
            )
            and interaction.user.guild_permissions.administrator
        ):
            allowed = True

        if not allowed:

            await interaction.response.send_message(
                "❌ You don't have permission to close this ticket.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 Are you sure you want to close this ticket?",
            view=CloseConfirmView(),
            ephemeral=True
        )


# ============================================================
# CREATE TICKET
# ============================================================

class TicketView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="ticket:create"
    )
    async def create_ticket(
        self,
        interaction,
        button
    ):

        print(
            f"[TICKET] CREATE BUTTON CALLBACK "
            f"from {interaction.user}"
        )

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )

            return

        # Acknowledge immediately.
        await interaction.response.defer(
            ephemeral=True
        )

        print(
            "[TICKET] Interaction acknowledged."
        )

        # ----------------------------------------------------
        # EXISTING TICKET
        # ----------------------------------------------------

        for channel in guild.text_channels:

            if channel.topic == (
                f"ticket_owner:{interaction.user.id}"
            ):

                await interaction.followup.send(
                    (
                        "❌ You already have a ticket:\n"
                        f"{channel.mention}"
                    ),
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category = get_ticket_category(
            guild
        )

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        staff_role = get_staff_role(
            guild
        )

        if staff_role:

            overwrites[staff_role] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                    manage_messages=True,
                    manage_channels=True
                )
            )

        # ----------------------------------------------------
        # CHANNEL NAME
        # ----------------------------------------------------

        name = interaction.user.name.lower()

        name = name.replace(
            " ",
            "-"
        )

        name = name.replace(
            "_",
            "-"
        )

        name = "".join(
            x
            for x in name
            if x.isalnum() or x == "-"
        )

        if not name:
            name = "user"

        channel_name = f"ticket-{name}"

        # ----------------------------------------------------
        # CREATE CHANNEL
        # ----------------------------------------------------

        try:

            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=(
                    f"ticket_owner:"
                    f"{interaction.user.id}"
                ),
                reason=(
                    f"Ticket created by "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:

            print(
                "[TICKET] Missing Manage Channels."
            )

            await interaction.followup.send(
                (
                    "❌ I cannot create the ticket.\n\n"
                    "Give me the **Manage Channels** "
                    "permission."
                ),
                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"[TICKET] Channel creation error: {e}"
            )

            await interaction.followup.send(
                (
                    "❌ Failed to create the ticket."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                "Please describe your issue and "
                "wait for a member of the support "
                "team.\n\n"
                "Use **🔒 Close Ticket** when you're done."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Owner",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🟢 Open",
            inline=True
        )

        # ----------------------------------------------------
        # SEND MESSAGE
        # ----------------------------------------------------

        try:

            await channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=TicketControlView()
            )

        except Exception as e:

            print(
                f"[TICKET] Message error: {e}"
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        await interaction.followup.send(
            (
                "🎫 **Ticket created!**\n"
                f"{channel.mention}"
            ),
            ephemeral=True
        )

        print(
            f"[TICKET] SUCCESS: {channel.name}"
        )

        await log_ticket(
            guild,
            (
                f"🎫 `{channel.name}` "
                f"created by "
                f"{interaction.user.mention}"
            )
        )