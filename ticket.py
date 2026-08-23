# ticket.py

import discord
from discord import app_commands
from discord.ui import View


# ============================================================
# CONFIG
# ============================================================

# Category where tickets are created.
TICKET_CATEGORY_ID = 1540454800557084792

# Channel where ticket logs are sent.
# Set to 0 to disable logs.
TICKET_LOG_CHANNEL_ID = 1540674475635245218

# Staff role allowed to manage tickets.
STAFF_ROLE_ID = 1540501461698482197


# ============================================================
# TICKET TYPES
# ============================================================

TICKET_TYPES = {
    "refunds": {
        "name": "Refunds",
        "emoji": "💰",
        "description": "Open a ticket for a refund."
    },

    "bugs": {
        "name": "Bugs",
        "emoji": "🐛",
        "description": "Report a bug or technical issue."
    },

    "questions": {
        "name": "Questions",
        "emoji": "❓",
        "description": "Ask a question."
    },

    "general": {
        "name": "General",
        "emoji": "💬",
        "description": "Open a general support ticket."
    },

    "partnership": {
        "name": "Partnership Requests",
        "emoji": "🤝",
        "description": "Request a partnership."
    },

    "report": {
        "name": "Report User",
        "emoji": "🚨",
        "description": "Report another user."
    },

    "appeal": {
        "name": "Ban Appeals",
        "emoji": "🔨",
        "description": "Appeal a server ban."
    }
}


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


def is_ticket_channel(channel):

    if channel is None:
        return False

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return False

    if not channel.topic:
        return False

    return channel.topic.startswith(
        "ticket_owner:"
    )


async def log_ticket(
    guild,
    message
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
            message
        )

    except Exception as e:

        print(
            f"[TICKET] Log error: {e}"
        )


# ============================================================
# CLOSE TICKET
# ============================================================

async def close_ticket(
    interaction
):

    channel = interaction.channel

    if channel is None:
        return

    if not is_ticket_channel(
        channel
    ):

        await interaction.response.send_message(
            "❌ This command/button can only be used inside a ticket.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # GET OWNER
    # --------------------------------------------------------

    owner_id = None

    try:

        owner_id = int(
            channel.topic.replace(
                "ticket_owner:",
                ""
            ).split("|")[0]
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # CHECK PERMISSION
    # --------------------------------------------------------

    allowed = False

    if owner_id == interaction.user.id:
        allowed = True

    if is_staff(
        interaction.user
    ):
        allowed = True

    if not allowed:

        await interaction.response.send_message(
            "❌ You don't have permission to close this ticket.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # ALREADY CLOSED
    # --------------------------------------------------------

    if "|closed" in channel.topic:

        await interaction.response.send_message(
            "🔴 This ticket is already closed.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # UPDATE TOPIC
    # --------------------------------------------------------

    new_topic = (
        channel.topic
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

    # --------------------------------------------------------
    # REMOVE USER SEND PERMISSION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SEND CLOSED MESSAGE
    # --------------------------------------------------------

    embed = discord.Embed(
        title="🔴 Ticket Closed",
        description=(
            "This ticket has been closed.\n\n"
            "Staff can permanently delete this "
            "ticket with `/deleteticket`."
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
        value="🔴 Closed",
        inline=True
    )

    try:

        await channel.send(
            embed=embed
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    await log_ticket(
        interaction.guild,
        (
            f"🔴 Ticket `{channel.name}` "
            f"closed by "
            f"{interaction.user.mention}."
        )
    )


# ============================================================
# TICKET TYPE VIEW
# ============================================================

class TicketTypeView(View):

    def __init__(self):

        super().__init__(
            timeout=60
        )

    async def create_ticket(
        self,
        interaction,
        ticket_type
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )

            return

        # ACKNOWLEDGE IMMEDIATELY
        await interaction.response.defer(
            ephemeral=True
        )

        print(
            f"[TICKET] {interaction.user} selected "
            f"{ticket_type}"
        )

        # ----------------------------------------------------
        # CHECK EXISTING
        # ----------------------------------------------------

        for channel in guild.text_channels:

            if channel.topic and channel.topic.startswith(
                f"ticket_owner:{interaction.user.id}"
            ):

                await interaction.followup.send(
                    (
                        "❌ You already have an open ticket:\n"
                        f"{channel.mention}"
                    ),
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # GET TYPE
        # ----------------------------------------------------

        data = TICKET_TYPES[
            ticket_type
        ]

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

            overwrites[
                staff_role
            ] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True,
                manage_channels=True
            )

        # ----------------------------------------------------
        # CHANNEL NAME
        # ----------------------------------------------------

        username = (
            interaction.user.name
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
        )

        username = "".join(
            char
            for char in username
            if char.isalnum()
            or char == "-"
        )

        if not username:
            username = "user"

        channel_name = (
            f"{ticket_type}-{username}"
        )

        # ----------------------------------------------------
        # CREATE
        # ----------------------------------------------------

        try:

            category = get_ticket_category(
                guild
            )

            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=(
                    f"ticket_owner:"
                    f"{interaction.user.id}"
                    f"|type:{ticket_type}"
                ),
                reason=(
                    f"{data['name']} ticket "
                    f"created by "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:

            await interaction.followup.send(
                (
                    "❌ I cannot create tickets.\n\n"
                    "Give the bot **Manage Channels**."
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

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title=(
                f"{data['emoji']} "
                f"{data['name']}"
            ),
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                f"{data['description']}\n\n"
                "Please provide all relevant information "
                "and wait for staff to respond.\n\n"
                "When finished, use **🔒 Close Ticket**."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Ticket Type",
            value=(
                f"{data['emoji']} "
                f"{data['name']}"
            ),
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🟢 Open",
            inline=True
        )

        embed.add_field(
            name="Owner",
            value=interaction.user.mention,
            inline=True
        )

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

        try:

            await channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=TicketControlView()
            )

        except Exception as e:

            print(
                f"[TICKET] Send error: {e}"
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        await interaction.followup.send(
            (
                f"{data['emoji']} "
                f"Your {data['name']} ticket has "
                f"been created:\n"
                f"{channel.mention}"
            ),
            ephemeral=True
        )

        await log_ticket(
            guild,
            (
                f"🎫 `{channel.name}` "
                f"({data['name']}) created by "
                f"{interaction.user.mention}"
            )
        )

        print(
            f"[TICKET] Created {channel.name}"
        )

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    @discord.ui.button(
        label="Refunds",
        emoji="💰",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:type:refunds"
    )
    async def refunds(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "refunds"
        )

    @discord.ui.button(
        label="Bugs",
        emoji="🐛",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:type:bugs"
    )
    async def bugs(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "bugs"
        )

    @discord.ui.button(
        label="Questions",
        emoji="❓",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:type:questions"
    )
    async def questions(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "questions"
        )

    @discord.ui.button(
        label="General",
        emoji="💬",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:type:general"
    )
    async def general(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "general"
        )

    @discord.ui.button(
        label="Partnership",
        emoji="🤝",
        style=discord.ButtonStyle.success,
        custom_id="ticket:type:partnership"
    )
    async def partnership(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "partnership"
        )

    @discord.ui.button(
        label="Report User",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:type:report"
    )
    async def report(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "report"
        )

    @discord.ui.button(
        label="Ban Appeals",
        emoji="🔨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:type:appeal"
    )
    async def appeal(
        self,
        interaction,
        button
    ):
        await self.create_ticket(
            interaction,
            "appeal"
        )


# ============================================================
# CREATE TICKET PANEL BUTTON
# ============================================================

class TicketView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:create"
    )
    async def create_ticket_button(
        self,
        interaction,
        button
    ):

        # ACKNOWLEDGE IMMEDIATELY
        await interaction.response.send_message(
            (
                "🎫 **Choose a ticket type:**\n\n"
                "Select the button that best describes "
                "your request."
            ),
            view=TicketTypeView(),
            ephemeral=True
        )


# ============================================================
# TICKET CONTROL BUTTONS
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
        custom_id="ticket:close"
    )
    async def close(
        self,
        interaction,
        button
    ):

        await close_ticket(
            interaction
        )


# ============================================================
# DELETE TICKET SLASH COMMAND
# ============================================================

class TicketCommands(discord.Cog):

    def __init__(
        self,
        client
    ):

        self.client = client

    @app_commands.command(
        name="deleteticket",
        description="Permanently delete the current ticket."
    )
    async def deleteticket(
        self,
        interaction: discord.Interaction
    ):

        channel = interaction.channel
        guild = interaction.guild

        # ----------------------------------------------------
        # MUST BE TICKET
        # ----------------------------------------------------

        if not is_ticket_channel(
            channel
        ):

            await interaction.response.send_message(
                (
                    "❌ `/deleteticket` can only be "
                    "used inside a ticket channel."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # STAFF ONLY
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ACKNOWLEDGE
        # ----------------------------------------------------

        await interaction.response.send_message(
            "🗑️ Deleting this ticket...",
            ephemeral=True
        )

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        if guild:

            await log_ticket(
                guild,
                (
                    f"🗑️ Ticket `{channel.name}` "
                    f"permanently deleted by "
                    f"{interaction.user.mention}."
                )
            )

        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

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

        except Exception as e:

            print(
                f"[TICKET] Delete error: {e}"
            )


# ============================================================
# SETUP
# ============================================================

async def setup_ticket_system(
    client
):

    client.add_view(
        TicketView()
    )

    client.add_view(
        TicketControlView()
    )

    await client.add_cog(
        TicketCommands(
            client
        )
    )

    print(
        "[TICKET] Ticket system loaded."
    )