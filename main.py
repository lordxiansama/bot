import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
DB_FILE = "matriculas.json"
SECURITY_ANSWER = "gazzo" 

# --- ROLE IDs ---
BASE_ROLE_ID = 1484790618894110741  
GUEST_ROLE_ID = 1484793334638841886 
YEAR_ROLES = {
    "25": 1485472578977009796,  
    "24": 1485472578456780811,  
    "23": 1485472569048957041   
}

# --- DATABASE LOGIC ---
def load_matriculas():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except:
        return []

def remove_matricula(matricula):
    data = load_matriculas()
    if matricula in data:
        data.remove(matricula)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    return False

# --- STUDENT VERIFICATION MODAL ---
class VerifyModal(discord.ui.Modal, title="Verificación de Estudiante"):
    cafeteria = discord.ui.TextInput(
        label="¿Nombre de la cafetería con G?",
        placeholder="Escribe aquí...",
        required=True
    )
    
    matricula = discord.ui.TextInput(
        label="Ingresa tu Matrícula",
        placeholder="Ejemplo: 25123",
        required=True,
        min_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.cafeteria.value.strip().lower() != SECURITY_ANSWER.lower():
            embed = discord.Embed(title="❌ Error", description="Respuesta de seguridad incorrecta.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        val_matricula = self.matricula.value.strip()
        if remove_matricula(val_matricula):
            guild = interaction.guild
            roles_to_add = []
            
            base_role = guild.get_role(BASE_ROLE_ID)
            if base_role: roles_to_add.append(base_role)

            prefix = val_matricula[:2]
            if prefix in YEAR_ROLES:
                year_role = guild.get_role(YEAR_ROLES[prefix])
                if year_role: roles_to_add.append(year_role)

            if roles_to_add:
                await interaction.user.add_roles(*roles_to_add)
                embed = discord.Embed(
                    title="✅ ¡Verificado!",
                    description=f"Bienvenido Estudiante. Matrícula **{val_matricula}** aceptada.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Matrícula no encontrada o ya usada.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

# --- CHOICE BUTTONS VIEW ---
class ChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="Estudiante PFLC", style=discord.ButtonStyle.primary, emoji="🎓")
    async def estudiante_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

    @discord.ui.button(label="Visitante", style=discord.ButtonStyle.secondary, emoji="👋")
    async def visitante_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        guest_role = guild.get_role(GUEST_ROLE_ID)
        
        if guest_role:
            try:
                await interaction.user.add_roles(guest_role)
                embed = discord.Embed(
                    title="✅ Acceso de Visitante",
                    description="Se te ha asignado el rol de **Visitante**. ¡Disfruta el servidor!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("No tengo permisos para darte el rol.", ephemeral=True)
        else:
            await interaction.response.send_message("El rol de visitante no está configurado correctamente.", ephemeral=True)

# --- BOT MAIN SETUP ---
class MyBot(commands.Bot):
    def __init__(self):
        # We use Intents.all() to make sure role management works perfectly
        intents = discord.Intents.all()
        
        # Setting the status right here in the constructor
        status_msg = discord.Game(name="¡Hola! Soy Jaguabot, el bot de la PFLC.")
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            activity=status_msg,
            status=discord.Status.online
        )

    async def setup_hook(self):
        # This keeps the buttons working even if the bot restarts
        self.add_view(ChoiceView())
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="verify", description="Inicia tu proceso de ingreso")
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Sistema de Ingreso",
        description="¿Eres Estudiante de la PFLC o un Visitante?",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Selecciona una opción abajo para continuar.")
    await interaction.response.send_message(embed=embed, view=ChoiceView(), ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

if __name__ == "__main__":
    bot.run(TOKEN)
