# ticket.py

import discord
from discord import app_commands
from discord.ui import View


# ============================================================
# CONFIG
# ============================================================

# Put your ticket CATEGORY ID here.
TICKET_CATEGORY_ID = 1540454800557084792

# Put your ticket LOG CHANNEL ID here.
# Use 0 if you don't want ticket logs.
TICKET_LOG_CHANNEL_ID = 1540674475635245218

# Put your STAFF ROLE ID here.
STAFF_ROLE_ID = 1541132281157128293


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


def is_staff(member):
    if not isinstance(
        member,
        discord.Member
    ):
        return False

    if member.guild_permissions.administrator:
        return True

    role = get_staff_role(
        member.guild
    )

    if role is None:
        return False

    return role in member.roles


def is_ticket(channel):
    return (
        isinstance(
            channel,
            discord.TextChannel
        )
        and channel.topic is not None
        and channel.topic.startswith(
            "ticket_owner:"
        )
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
        await channel.send(
            text
        )
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
        f"[TICKET] {interaction.user} "
        f"selected {ticket_type}"
    )

    # ========================================================
    # CHECK FOR EXISTING OPEN TICKET
    # ========================================================

    for channel in guild.text_channels:

        if not channel.topic:
            continue

        if not channel.topic.startswith(
            f"ticket_owner:{interaction.user.id}"
        ):
            continue

        if "|closed" in channel.topic:
            continue

        await interaction.followup.send(
            (
                "❌ You already have an open ticket:\n"
                f"{channel.mention}"
            ),
            ephemeral=True
        )

        return

    # ========================================================
    # TICKET TYPE
    # ========================================================

    emoji, ticket_name = TICKET_TYPES[
        ticket_type
    ]

    # ========================================================
    # PERMISSIONS
    # ========================================================

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

    # ========================================================
    # CHANNEL NAME
    # ========================================================

    username = (
        interaction.user.name
        .lower()
        .replace(
            " ",
            "-"
        )
        .replace(
            "_",
            "-"
        )
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
        f"{ticket_type}-{username}"
    )

    # ========================================================
    # CREATE CHANNEL
    # ========================================================

    try:

        channel = await guild.create_text_channel(
            channel_name,
            category=get_category(guild),
            overwrites=overwrites,
            topic=(
                f"ticket_owner:"
                f"{interaction.user.id}"
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
                "❌ I cannot create the ticket.\n\n"
                "Make sure the bot has "
                "**Manage Channels** permission."
            ),
            ephemeral=True
        )

        return

    except discord.HTTPException as e:

        print(
            f"[TICKET] Discord error: {e}"
        )

        await interaction.followup.send(
            (
                "❌ Discord returned an error "
                "while creating the ticket."
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

    # ========================================================
    # TICKET EMBED
    # ========================================================

    embed = discord.Embed(
        title=(
            f"{emoji} {ticket_name}"
        ),
        description=(
            f"Welcome {interaction.user.mention}!\n\n"
            f"You opened a **{ticket_name}** ticket.\n\n"
            "Please explain your request clearly "
            "and provide any information that may "
            "help our staff.\n\n"
            "When you are finished, click "
            "**🔒 Close Ticket**."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Ticket Type",
        value=(
            f"{emoji} {ticket_name}"
        ),
        inline=True
    )

    embed.add_field(
        name="Status",
        value="🟢 OPEN",
        inline=True
    )

    embed.add_field(
        name="Ticket Owner",
        value=interaction.user.mention,
        inline=True
    )

    embed.set_footer(
        text=f"Ticket ID: {channel.id}"
    )

    # ========================================================
    # SEND TICKET MESSAGE
    # ========================================================

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

    # ========================================================
    # USER RESPONSE
    # ========================================================

    await interaction.followup.send(
        (
            f"{emoji} Your **{ticket_name}** ticket "
            "has been created:\n"
            f"{channel.mention}"
        ),
        ephemeral=True
    )

    # ========================================================
    # LOG
    # ========================================================

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
# MAIN TICKET PANEL
# ============================================================

class TicketPanelView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # ========================================================
    # ROW 1
    # ========================================================

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

    # ========================================================
    # ROW 2
    # ========================================================

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
        label="Partnership Requests",
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

    # ========================================================
    # ROW 3
    # ========================================================

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

        # ====================================================
        # CHECK TICKET
        # ====================================================

        if not is_ticket(channel):

            await interaction.response.send_message(
                "❌ This isn't a ticket channel.",
                ephemeral=True
            )

            return

        # ====================================================
        # GET OWNER
        # ====================================================

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

        # ====================================================
        # CHECK PERMISSION
        # ====================================================

        if (
            interaction.user.id != owner_id
            and not is_staff(
                interaction.user
            )
        ):

            await interaction.response.send_message(
                (
                    "❌ You don't have permission "
                    "to close this ticket."
                ),
                ephemeral=True
            )

            return

        # ====================================================
        # ALREADY CLOSED
        # ====================================================

        if "|closed" in channel.topic:

            await interaction.response.send_message(
                "🔴 This ticket is already closed.",
                ephemeral=True
            )

            return

        # ====================================================
        # ACKNOWLEDGE
        # ====================================================

        await interaction.response.defer(
            ephemeral=True
        )

        # ====================================================
        # CHANGE STATUS
        # ====================================================

        new_topic = (
            channel.topic
            .replace(
                "|open",
                ""
            )
            + "|closed"
        )

        try:

            await channel.edit(
                topic=new_topic
            )

        except Exception as e:

            print(
                f"[TICKET] Could not update topic: {e}"
            )

        # ====================================================
        # REMOVE USER SEND PERMISSION
        # ====================================================

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

        # ====================================================
        # CLOSED MESSAGE
        # ====================================================

        embed = discord.Embed(
            title="🔴 Ticket Closed",
            description=(
                "This ticket has been closed.\n\n"
                "Staff can permanently delete this "
                "ticket with:\n\n"
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
# /DELETETICKET
# ============================================================

async def delete_ticket_command(
    interaction: discord.Interaction
):

    channel = interaction.channel

    # ========================================================
    # MUST BE TICKET
    # ========================================================

    if not is_ticket(channel):

        await interaction.response.send_message(
            (
                "❌ You must run `/deleteticket` "
                "inside a ticket channel."
            ),
            ephemeral=True
        )

        return

    # ========================================================
    # STAFF ONLY
    # ========================================================

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

    # ========================================================
    # ACKNOWLEDGE
    # ========================================================

    await interaction.response.send_message(
        "🗑️ Deleting this ticket...",
        ephemeral=True
    )

    # ========================================================
    # LOG
    # ========================================================

    await log_ticket(
        interaction.guild,
        (
            f"🗑️ `{channel.name}` permanently "
            f"deleted by "
            f"{interaction.user.mention}"
        )
    )

    # ========================================================
    # DELETE
    # ========================================================

    try:

        await channel.delete(
            reason=(
                f"Ticket deleted by "
                f"{interaction.user}"
            )
        )

    except discord.Forbidden:

        print(
            "[TICKET] Missing Manage Channels "
            "permission."
        )

    except discord.HTTPException as e:

        print(
            f"[TICKET] Discord delete error: {e}"
        )

    except Exception as e:

        print(
            f"[TICKET] Delete error: {e}"
        )


# ============================================================
# SETUP
# ============================================================

async def setup_ticket_system(
    bot,
    tree
):

    # Persistent ticket panel.
    bot.add_view(
        TicketPanelView()
    )

    # Persistent close button.
    bot.add_view(
        TicketControlView()
    )

    # --------------------------------------------------------
    # REGISTER /DELETETICKET
    # --------------------------------------------------------

    existing = tree.get_command(
        "deleteticket"
    )

    if existing is None:

        command = app_commands.Command(
            name="deleteticket",
            description=(
                "Permanently delete the current ticket."
            ),
            callback=delete_ticket_command
        )

        tree.add_command(
            command
        )

    print(
        "[TICKET] Ticket system loaded."
    )