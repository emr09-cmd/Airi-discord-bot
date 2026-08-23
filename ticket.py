# ticket.py

import discord
from discord import app_commands
from discord.ui import View


# ============================================================
# CONFIG
# ============================================================

TICKET_CATEGORY_ID = 1540454800557084792
TICKET_LOG_CHANNEL_ID = 1540674475635245218
STAFF_ROLE_ID = 1540501461698482197


# ============================================================
# TICKET TYPES
# ============================================================

TICKET_TYPES = {
    "refunds": ("💰", "Refunds"),
    "bugs": ("🐛", "Bugs"),
    "questions": ("❓", "Questions"),
    "general": ("💬", "General"),
    "partnership": ("🤝", "Partnership Requests"),
    "report": ("🚨", "Report User"),
    "appeal": ("🔨", "Ban Appeals"),
}


# ============================================================
# HELPERS
# ============================================================

def get_category(guild):

    if TICKET_CATEGORY_ID == 0:
        return None

    channel = guild.get_channel(TICKET_CATEGORY_ID)

    if isinstance(channel, discord.CategoryChannel):
        return channel

    return None


def get_staff_role(guild):

    if STAFF_ROLE_ID == 0:
        return None

    return guild.get_role(STAFF_ROLE_ID)


def is_staff(member):

    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    role = get_staff_role(member.guild)

    if role is None:
        return False

    return role in member.roles


def is_ticket(channel):

    return (
        isinstance(channel, discord.TextChannel)
        and channel.topic is not None
        and channel.topic.startswith("ticket_owner:")
    )


async def log_ticket(guild, text):

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
# CREATE TICKET
# ============================================================

async def create_ticket(
    interaction,
    ticket_type
):

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(
            "❌ This can only be used inside a server.",
            ephemeral=True
        )

        return

    # Acknowledge immediately.
    await interaction.response.defer(
        ephemeral=True
    )

    print(
        f"[TICKET] {interaction.user} selected "
        f"{ticket_type}"
    )

    # --------------------------------------------------------
    # CHECK EXISTING OPEN TICKET
    # --------------------------------------------------------

    for channel in guild.text_channels:

        if (
            channel.topic
            and channel.topic.startswith(
                f"ticket_owner:{interaction.user.id}"
            )
            and "|closed" not in channel.topic
        ):

            await interaction.followup.send(
                (
                    "❌ You already have an open ticket:\n"
                    f"{channel.mention}"
                ),
                ephemeral=True
            )

            return

    # --------------------------------------------------------
    # TYPE
    # --------------------------------------------------------

    emoji, ticket_name = TICKET_TYPES[
        ticket_type
    ]

    # --------------------------------------------------------
    # PERMISSIONS
    # --------------------------------------------------------

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

    staff_role = get_staff_role(guild)

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

    # --------------------------------------------------------
    # CHANNEL NAME
    # --------------------------------------------------------

    username = (
        interaction.user.name
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
    )

    username = "".join(
        char
        for char in username
        if char.isalnum() or char == "-"
    )

    if not username:
        username = "user"

    channel_name = (
        f"{ticket_type}-{username}"
    )

    # --------------------------------------------------------
    # CREATE CHANNEL
    # --------------------------------------------------------

    try:

        channel = await guild.create_text_channel(
            channel_name,
            category=get_category(guild),
            overwrites=overwrites,
            topic=(
                f"ticket_owner:{interaction.user.id}"
                f"|type:{ticket_type}"
                f"|open"
            ),
            reason=(
                f"{ticket_name} ticket created by "
                f"{interaction.user}"
            )
        )

    except discord.Forbidden:

        await interaction.followup.send(
            (
                "❌ I cannot create tickets.\n\n"
                "Give the bot **Manage Channels** "
                "permission."
            ),
            ephemeral=True
        )

        return

    except Exception as e:

        print(
            f"[TICKET] Creation error: {e}"
        )

        await interaction.followup.send(
            "❌ Failed to create the ticket.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # EMBED
    # --------------------------------------------------------

    embed = discord.Embed(
        title=f"{emoji} {ticket_name}",
        description=(
            f"Welcome {interaction.user.mention}!\n\n"
            f"You opened a **{ticket_name}** ticket.\n\n"
            "Please explain your request clearly. "
            "A member of staff will assist you.\n\n"
            "When you're finished, click "
            "**🔒 Close Ticket**."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Type",
        value=f"{emoji} {ticket_name}",
        inline=True
    )

    embed.add_field(
        name="Status",
        value="🟢 OPEN",
        inline=True
    )

    embed.add_field(
        name="User",
        value=interaction.user.mention,
        inline=True
    )

    embed.set_footer(
        text=f"Ticket ID: {channel.id}"
    )

    # --------------------------------------------------------
    # SEND TICKET MESSAGE
    # --------------------------------------------------------

    try:

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketControlView()
        )

    except Exception as e:

        print(
            f"[TICKET] Could not send ticket message: {e}"
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    await interaction.followup.send(
        (
            f"{emoji} Your **{ticket_name}** ticket "
            f"has been created:\n"
            f"{channel.mention}"
        ),
        ephemeral=True
    )

    await log_ticket(
        guild,
        (
            f"🎫 `{channel.name}` created by "
            f"{interaction.user.mention} "
            f"({ticket_name})"
        )
    )

    print(
        f"[TICKET] Created #{channel.name}"
    )


# ============================================================
# MAIN PANEL
# ============================================================

class TicketPanelView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # --------------------------------------------------------
    # ROW 1
    # --------------------------------------------------------

    @discord.ui.button(
        label="Refunds",
        emoji="💰",
        style=discord.ButtonStyle.primary,
        row=0,
        custom_id="ticket:refunds"
    )
    async def refunds(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "refunds"
        )

    @discord.ui.button(
        label="Bugs",
        emoji="🐛",
        style=discord.ButtonStyle.primary,
        row=0,
        custom_id="ticket:bugs"
    )
    async def bugs(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "bugs"
        )

    @discord.ui.button(
        label="Questions",
        emoji="❓",
        style=discord.ButtonStyle.primary,
        row=0,
        custom_id="ticket:questions"
    )
    async def questions(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "questions"
        )

    # --------------------------------------------------------
    # ROW 2
    # --------------------------------------------------------

    @discord.ui.button(
        label="General",
        emoji="💬",
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="ticket:general"
    )
    async def general(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "general"
        )

    @discord.ui.button(
        label="Partnership",
        emoji="🤝",
        style=discord.ButtonStyle.success,
        row=1,
        custom_id="ticket:partnership"
    )
    async def partnership(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "partnership"
        )

    @discord.ui.button(
        label="Report User",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        row=1,
        custom_id="ticket:report"
    )
    async def report(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "report"
        )

    # --------------------------------------------------------
    # ROW 3
    # --------------------------------------------------------

    @discord.ui.button(
        label="Ban Appeals",
        emoji="🔨",
        style=discord.ButtonStyle.danger,
        row=2,
        custom_id="ticket:appeal"
    )
    async def appeal(
        self,
        interaction,
        button
    ):

        await create_ticket(
            interaction,
            "appeal"
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
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        row=0,
        custom_id="ticket:close"
    )
    async def close_ticket(
        self,
        interaction,
        button
    ):

        channel = interaction.channel

        if not is_ticket(channel):

            await interaction.response.send_message(
                "❌ This isn't a ticket channel.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # GET OWNER
        # ----------------------------------------------------

        owner_id = None

        try:

            owner_id = int(
                channel.topic
                .split("|")[0]
                .replace(
                    "ticket_owner:",
                    ""
                )
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # PERMISSION
        # ----------------------------------------------------

        if (
            interaction.user.id != owner_id
            and not is_staff(interaction.user)
        ):

            await interaction.response.send_message(
                (
                    "❌ You don't have permission "
                    "to close this ticket."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # ALREADY CLOSED
        # ----------------------------------------------------

        if "|closed" in channel.topic:

            await interaction.response.send_message(
                "🔴 This ticket is already closed.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # ACKNOWLEDGE
        # ----------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # UPDATE STATUS
        # ----------------------------------------------------

        new_topic = (
            channel.topic
            .replace("|open", "")
            + "|closed"
        )

        try:

            await channel.edit(
                topic=new_topic
            )

        except Exception as e:

            print(
                f"[TICKET] Topic error: {e}"
            )

        # ----------------------------------------------------
        # REMOVE USER SEND PERMISSION
        # ----------------------------------------------------

        if owner_id:

            owner = interaction.guild.get_member(
                owner_id
            )

            if owner:

                try:

                    await channel.set_permissions(
                        owner,
                        send_messages=False
                    )

                except Exception as e:

                    print(
                        f"[TICKET] Permission error: {e}"
                    )

        # ----------------------------------------------------
        # CLOSED MESSAGE
        # ----------------------------------------------------

        embed = discord.Embed(
            title="🔴 Ticket Closed",
            description=(
                "This ticket has been closed.\n\n"
                "Staff can permanently delete this "
                "channel using:\n\n"
                "`/deleteticket`"
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="Closed By",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🔴 CLOSED",
            inline=True
        )

        await channel.send(
            embed=embed
        )

        await interaction.followup.send(
            "🔴 Ticket closed.",
            ephemeral=True
        )

        await log_ticket(
            interaction.guild,
            (
                f"🔴 `{channel.name}` closed by "
                f"{interaction.user.mention}"
            )
        )


# ============================================================
# DELETE TICKET COMMAND
# ============================================================

async def delete_ticket_command(
    interaction: discord.Interaction
):

    channel = interaction.channel

    # Must be inside ticket.
    if not is_ticket(channel):

        await interaction.response.send_message(
            (
                "❌ You must run `/deleteticket` "
                "inside a ticket channel."
            ),
            ephemeral=True
        )

        return

    # Staff only.
    if not is_staff(
        interaction.user
    ):

        await interaction.response.send_message(
            (
                "❌ Only staff can permanently "
                "delete tickets."
            ),
            ephemeral=True
        )

        return

    # Acknowledge.
    await interaction.response.send_message(
        "🗑️ Deleting this ticket...",
        ephemeral=True
    )

    await log_ticket(
        interaction.guild,
        (
            f"🗑️ `{channel.name}` permanently "
            f"deleted by "
            f"{interaction.user.mention}"
        )
    )

    try:

        await channel.delete(
            reason=(
                f"Ticket deleted by "
                f"{interaction.user}"
            )
        )

    except discord.Forbidden:

        print(
            "[TICKET] Missing Manage Channels."
        )

    except Exception as e:

        print(
            f"[TICKET] Delete error: {e}"
        )


# ============================================================
# SETUP
# ============================================================

async def setup_ticket_system(
    bot
):

    bot.add_view(
        TicketPanelView()
    )

    bot.add_view(
        TicketControlView()
    )

    # Register /deleteticket
    bot.tree.add_command(
        app_commands.Command(
            name="deleteticket",
            description=(
                "Permanently delete the current ticket."
            ),
            callback=delete_ticket_command
        )
    )

    print(
        "[TICKET] Ticket system loaded."
    )