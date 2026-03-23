import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
ROLE_ID = 1484790618894110741
DB_FILE = "matriculas.json"
SECURITY_ANSWER = "gazzo"  # Case-insensitive answer to the cafeteria question

class VerificationBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sync slash commands with Discord
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = VerificationBot()

# --- DATABASE FUNCTIONS ---

def load_matriculas():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading database: {e}")
        return []

def remove_matricula(matricula):
    data = load_matriculas()
    if matricula in data:
        data.remove(matricula)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    return False

# --- MODAL SYSTEM (Verification Form) ---

class VerifyModal(discord.ui.Modal, title="Sistema de Verificación"):
    # Step 1 Input
    cafeteria = discord.ui.TextInput(
        label="¿Cuál es el nombre de la cafetería con G?",
        placeholder="Escribe el nombre aquí...",
        required=True,
        min_length=3
    )
    
    # Step 2 Input
    matricula = discord.ui.TextInput(
        label="Ingresa tu Matrícula",
        placeholder="Ejemplo: A01234567",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Check Security Question (Case Insensitive)
        if self.cafeteria.value.strip().lower() != SECURITY_ANSWER.lower():
            embed = discord.Embed(
                title="❌ Error de Seguridad",
                description="La respuesta a la pregunta de seguridad es incorrecta.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # 2. Check Matrícula in Database
        matricula_input = self.matricula.value.strip()
        if remove_matricula(matricula_input):
            # Success logic
            guild = interaction.guild
            role = guild.get_role(ROLE_ID)
            
            if role:
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="✅ Verificación Exitosa",
                        description=f"Bienvenido/a. Tu matrícula **{matricula_input}** ha sido validada y el rol ha sido asignado.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("Error: No tengo permisos para asignar roles. Contacta a un admin.", ephemeral=True)
            else:
                await interaction.response.send_message("Error: El rol de verificación no existe en el servidor.", ephemeral=True)
        else:
            # Fail logic
            embed = discord.Embed(
                title="❌ Matrícula Inválida",
                description="La matrícula ingresada no existe o ya fue utilizada.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# --- SLASH COMMAND ---

@bot.tree.command(name="verify", description="Inicia tu proceso de verificación de estudiante")
@app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id)) # 1 attempt per minute
async def verify(interaction: discord.Interaction):
    # Ensure command is used in a guild
    if not interaction.guild:
        return await interaction.response.send_message("Este comando solo funciona en el servidor.")

    # Send the modal
    await interaction.response.send_modal(VerifyModal())

# Error handler for cooldowns
@verify.error
async def verify_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏳ Cooldown",
            description=f"Por favor espera {error.retry_after:.1f} segundos antes de intentar de nuevo.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: No TOKEN found in environment variables.")
    else:
        bot.run(TOKEN)
