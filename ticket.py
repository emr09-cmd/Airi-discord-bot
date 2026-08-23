# ticket.py

import discord
from discord.ui import View


# ============================================================
# CONFIG
# ============================================================

# Category where tickets will be created.
TICKET_CATEGORY_ID = 1540454800557084792

# Channel where ticket logs will be sent.
# Set to 0 to disable logs.
TICKET_LOG_CHANNEL_ID = 1540674475635245218

# Staff role that can see/manage tickets.
# Set to 0 to disable staff-role permissions.
STAFF_ROLE_ID = 1540501461698482197


# ============================================================
# HELPERS
# ============================================================

def get_ticket_category(guild: discord.Guild):
    if TICKET_CATEGORY_ID == 0:
        return None

    channel = guild.get_channel(TICKET_CATEGORY_ID)

    if isinstance(channel, discord.CategoryChannel):
        return channel

    return None


def get_staff_role(guild: discord.Guild):
    if STAFF_ROLE_ID == 0:
        return None

    return guild.get_role(STAFF_ROLE_ID)


async def log_ticket(guild: discord.Guild, text: str):
    if TICKET_LOG_CHANNEL_ID == 0:
        return

    channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)

    if channel is None:
        try:
            channel = await guild.fetch_channel(
                TICKET_LOG_CHANNEL_ID
            )
        except Exception as e:
            print(f"[TICKET] Could not find log channel: {e}")
            return

    try:
        await channel.send(text)
    except Exception as e:
        print(f"[TICKET] Could not send log: {e}")


# ============================================================
# CLOSE CONFIRMATION
# ============================================================

class CloseConfirmView(View):

    def __init__(self):
        super().__init__(timeout=30)

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

        # Acknowledge immediately.
        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        if guild is not None:
            await log_ticket(
                guild,
                (
                    f"🔒 Ticket `{channel.name}` "
                    f"closed by "
                    f"{interaction.user.mention}."
                )
            )

        try:
            await channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )

        except discord.Forbidden:
            print(
                "[TICKET] Missing permission to delete ticket."
            )

        except discord.HTTPException as e:
            print(
                f"[TICKET] Discord error deleting ticket: {e}"
            )

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
        super().__init__(timeout=None)

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
        guild = interaction.guild

        if channel is None or guild is None:
            return

        # ----------------------------------------------------
        # CHECK PERMISSIONS
        # ----------------------------------------------------

        allowed = False

        # Ticket owner.
        if channel.topic:
            owner_prefix = "ticket_owner:"

            if channel.topic.startswith(owner_prefix):

                try:
                    owner_id = int(
                        channel.topic[len(owner_prefix):]
                    )

                    if interaction.user.id == owner_id:
                        allowed = True

                except ValueError:
                    pass

        # Staff role.
        staff_role = get_staff_role(guild)

        if staff_role is not None:

            if isinstance(interaction.user, discord.Member):

                if staff_role in interaction.user.roles:
                    allowed = True

        # Administrator.
        if isinstance(interaction.user, discord.Member):

            if interaction.user.guild_permissions.administrator:
                allowed = True

        if not allowed:

            await interaction.response.send_message(
                "❌ You don't have permission to close this ticket.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # ASK FOR CONFIRMATION
        # ----------------------------------------------------

        await interaction.response.send_message(
            "🔒 Are you sure you want to close this ticket?",
            view=CloseConfirmView(),
            ephemeral=True
        )


# ============================================================
# CREATE TICKET VIEW
# ============================================================

class TicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

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

        if guild is None:

            await interaction.response.send_message(
                "❌ This button can only be used inside a server.",
                ephemeral=True
            )

            return

        # ====================================================
        # IMPORTANT:
        # ACKNOWLEDGE THE INTERACTION IMMEDIATELY.
        # ====================================================

        await interaction.response.defer(
            ephemeral=True
        )

        print(
            f"[TICKET] {interaction.user} "
            f"clicked Create Ticket"
        )

        # ====================================================
        # CHECK EXISTING TICKET
        # ====================================================

        existing_ticket = None

        for channel in guild.text_channels:

            if channel.topic == (
                f"ticket_owner:{interaction.user.id}"
            ):

                existing_ticket = channel
                break

        if existing_ticket:

            await interaction.followup.send(
                (
                    "❌ You already have an open ticket:\n"
                    f"{existing_ticket.mention}"
                ),
                ephemeral=True
            )

            return

        # ====================================================
        # CATEGORY
        # ====================================================

        category = get_ticket_category(guild)

        # ====================================================
        # PERMISSIONS
        # ====================================================

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

        # ====================================================
        # STAFF ROLE
        # ====================================================

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

        # ====================================================
        # CHANNEL NAME
        # ====================================================

        username = interaction.user.name.lower()

        username = username.replace(" ", "-")
        username = username.replace("_", "-")

        username = "".join(
            char
            for char in username
            if char.isalnum() or char == "-"
        )

        if not username:
            username = "user"

        channel_name = f"ticket-{username}"

        # ====================================================
        # CREATE CHANNEL
        # ====================================================

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

            print(
                "[TICKET] Discord denied channel creation."
            )

            await interaction.followup.send(
                (
                    "❌ I don't have permission to "
                    "create ticket channels.\n\n"
                    "Give the bot **Manage Channels** "
                    "permission."
                ),
                ephemeral=True
            )

            return

        except discord.HTTPException as e:

            print(
                f"[TICKET] Discord HTTP error: {e}"
            )

            await interaction.followup.send(
                (
                    "❌ Discord returned an error while "
                    "creating the ticket."
                ),
                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"[TICKET] Unexpected error: {e}"
            )

            await interaction.followup.send(
                (
                    "❌ An unexpected error occurred "
                    "while creating the ticket."
                ),
                ephemeral=True
            )

            return

        # ====================================================
        # EMBED
        # ====================================================

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                "Please describe your issue below.\n\n"
                "A member of the support team will "
                "assist you as soon as possible.\n\n"
                "When your issue has been resolved, "
                "press **🔒 Close Ticket**."
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

        embed.set_footer(
            text=f"Ticket ID: {ticket_channel.id}"
        )

        # ====================================================
        # SEND TICKET MESSAGE
        # ====================================================

        try:

            await ticket_channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=TicketControlView()
            )

        except Exception as e:

            print(
                f"[TICKET] Could not send ticket message: {e}"
            )

        # ====================================================
        # RESPOND TO USER
        # ====================================================

        await interaction.followup.send(
            (
                "🎫 **Ticket created!**\n"
                f"{ticket_channel.mention}"
            ),
            ephemeral=True
        )

        # ====================================================
        # LOG
        # ====================================================

        await log_ticket(
            guild,
            (
                f"🎫 Ticket `{ticket_channel.name}` "
                f"created by "
                f"{interaction.user.mention}."
            )
        )

        print(
            f"[TICKET] Created #{ticket_channel.name}"
        )


# ============================================================
# SETUP
# ============================================================

def setup_ticket_system(client: discord.Client):

    client.add_view(TicketView())
    client.add_view(TicketControlView())

    print("[TICKET] Persistent ticket buttons loaded.")