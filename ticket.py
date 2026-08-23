# ticket.py

import discord
from discord.ui import View, Button


# ============================================================
# CONFIG
# ============================================================

# Discord CATEGORY ID where tickets should be created.
#
# Example:
# TICKET_CATEGORY_ID = 123456789012345678
#
# Leave as 0 if you don't want to use a category.

TICKET_CATEGORY_ID = 1540454800557084792


# Discord CHANNEL ID where ticket logs should be sent.
#
# Leave as 0 to disable ticket logs.

TICKET_LOG_CHANNEL_ID = 1540674475635245218


# Discord ROLE ID for your staff/support team.
#
# Staff with this role will be able to see tickets.
#
# Leave as 0 if you don't want to use a staff role.

STAFF_ROLE_ID = 1540501461698482197


# ============================================================
# GET CATEGORY
# ============================================================

def get_ticket_category(guild: discord.Guild):

    if TICKET_CATEGORY_ID == 0:
        return None

    channel = guild.get_channel(TICKET_CATEGORY_ID)

    if isinstance(channel, discord.CategoryChannel):
        return channel

    return None


# ============================================================
# GET STAFF ROLE
# ============================================================

def get_staff_role(guild: discord.Guild):

    if STAFF_ROLE_ID == 0:
        return None

    return guild.get_role(STAFF_ROLE_ID)


# ============================================================
# LOGGING
# ============================================================

async def log_ticket(
    guild: discord.Guild,
    message: str
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

        except Exception:
            return

    if channel is None:
        return

    try:
        await channel.send(message)

    except Exception:
        pass


# ============================================================
# CLOSE CONFIRMATION VIEW
# ============================================================

class CloseConfirmView(View):

    def __init__(self):
        super().__init__(timeout=30)

    # --------------------------------------------------------
    # CONFIRM CLOSE
    # --------------------------------------------------------

    @discord.ui.button(
        label="Confirm Close",
        style=discord.ButtonStyle.danger,
        emoji="🔒"
    )
    async def confirm_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        if channel is None:
            return

        await interaction.response.send_message(
            "🔒 Closing this ticket...",
            ephemeral=True
        )

        # Log ticket closure.
        if interaction.guild is not None:

            await log_ticket(
                interaction.guild,
                (
                    f"🔒 Ticket `{channel.name}` "
                    f"closed by "
                    f"{interaction.user.mention}."
                )
            )

        # Delete the ticket channel.
        try:

            await channel.delete(
                reason=(
                    f"Ticket closed by "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:

            try:
                await interaction.followup.send(
                    (
                        "❌ I don't have permission "
                        "to delete this ticket."
                    ),
                    ephemeral=True
                )
            except Exception:
                pass

        except discord.HTTPException:
            pass

    # --------------------------------------------------------
    # CANCEL
    # --------------------------------------------------------

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌"
    )
    async def cancel_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.edit_message(
            content="Ticket close cancelled.",
            view=None
        )


# ============================================================
# TICKET CONTROL VIEW
# ============================================================

class TicketControlView(View):

    def __init__(self):
        # Persistent view.
        super().__init__(timeout=None)

    # --------------------------------------------------------
    # CLOSE TICKET BUTTON
    # --------------------------------------------------------

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket:close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        if channel is None:
            return

        # Only allow the ticket owner or staff to close it.
        guild = interaction.guild

        if guild is None:
            return

        allowed = False

        # Check ticket owner.
        if channel.topic:

            expected = f"ticket_owner:{interaction.user.id}"

            if channel.topic == expected:
                allowed = True

        # Check staff role.
        staff_role = get_staff_role(guild)

        if staff_role is not None:

            if staff_role in interaction.user.roles:
                allowed = True

        # Also allow administrators.
        if isinstance(
            interaction.user,
            discord.Member
        ):

            if interaction.user.guild_permissions.administrator:
                allowed = True

        if not allowed:

            await interaction.response.send_message(
                (
                    "❌ You don't have permission "
                    "to close this ticket."
                ),
                ephemeral=True
            )

            return

        # Ask for confirmation.
        await interaction.response.send_message(
            (
                "🔒 **Close Ticket?**\n\n"
                "Are you sure you want to close "
                "this ticket?"
            ),
            view=CloseConfirmView(),
            ephemeral=True
        )


# ============================================================
# MAIN TICKET PANEL
# ============================================================

class TicketView(View):

    def __init__(self):
        # Persistent view.
        super().__init__(timeout=None)

    # --------------------------------------------------------
    # CREATE TICKET
    # --------------------------------------------------------

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="ticket:create"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        # Make sure this is a server.
        if guild is None:

            await interaction.response.send_message(
                (
                    "❌ Tickets can only be created "
                    "inside a server."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CHECK EXISTING TICKET
        # ----------------------------------------------------

        existing_ticket = None

        for channel in guild.text_channels:

            if channel.topic == (
                f"ticket_owner:{interaction.user.id}"
            ):
                existing_ticket = channel
                break

        if existing_ticket:

            await interaction.response.send_message(
                (
                    "❌ You already have an open ticket:\n"
                    f"{existing_ticket.mention}"
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # GET CATEGORY
        # ----------------------------------------------------

        category = get_ticket_category(guild)

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

        overwrites = {

            # Everyone cannot see tickets.
            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            # Ticket creator can see and use it.
            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        # ----------------------------------------------------
        # STAFF PERMISSIONS
        # ----------------------------------------------------

        staff_role = get_staff_role(guild)

        if staff_role is not None:

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
        # CREATE CHANNEL NAME
        # ----------------------------------------------------

        username = interaction.user.name.lower()

        username = (
            username
            .replace(" ", "-")
            .replace("_", "-")
        )

        username = "".join(
            character
            for character in username
            if character.isalnum()
            or character == "-"
        )

        if not username:
            username = "user"

        channel_name = (
            f"ticket-{username}"
        )

        # ----------------------------------------------------
        # CREATE TICKET CHANNEL
        # ----------------------------------------------------

        try:

            ticket_channel = (
                await guild.create_text_channel(
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
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ I don't have permission "
                    "to create ticket channels."
                ),
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                (
                    "❌ Discord failed to create "
                    "the ticket channel."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # TICKET EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                "Thanks for contacting support.\n\n"
                "Please describe your issue below. "
                "A member of the support team will "
                "help you as soon as possible.\n\n"
                "When your issue is resolved, press "
                "**Close Ticket**."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Ticket Owner",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🟢 Open",
            inline=True
        )

        embed.add_field(
            name="Ticket ID",
            value=str(ticket_channel.id),
            inline=False
        )

        embed.set_footer(
            text="Ticket system"
        )

        # ----------------------------------------------------
        # SEND TICKET MESSAGE
        # ----------------------------------------------------

        try:

            await ticket_channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=TicketControlView()
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        await interaction.response.send_message(
            (
                "🎫 Your ticket has been created!\n"
                f"{ticket_channel.mention}"
            ),
            ephemeral=True
        )

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        await log_ticket(
            guild,
            (
                f"🎫 Ticket `{ticket_channel.name}` "
                f"created by "
                f"{interaction.user.mention}."
            )
        )


# ============================================================
# SETUP FUNCTION
# ============================================================

def setup_ticket_system(
    client: discord.Client
):

    """
    Connects the ticket system to app.py.

    This registers the persistent ticket buttons
    so they continue working after bot restarts.
    """

    client.add_view(
        TicketView()
    )

    client.add_view(
        TicketControlView()
    )