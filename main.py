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
    except Exception as e:
        print(f"Error loading DB: {e}")
        return []

def remove_matricula(matricula):
    data = load_matriculas()
    if matricula in data:
        data.remove(matricula)
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving DB: {e}")
            return False
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
                try:
                    await interaction.user.add_roles(*roles_to_add)
                    embed = discord.Embed(
                        title="✅ ¡Verificado!",
                        description=f"Bienvenido Estudiante. Matrícula **{val_matricula}** aceptada.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("No tengo permisos para dar roles. Revisa la jerarquía.", ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Matrícula no encontrada o ya usada.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

# --- CHOICE BUTTONS VIEW (PERSISTENT) ---
class ChoiceView(discord.ui.View):
    def __init__(self):
        # Explicitly setting timeout=None for persistence
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Estudiante PFLC", 
        style=discord.ButtonStyle.primary, 
        emoji="🎓", 
        custom_id="btn_student_verify" # Explicit custom_id
    )
    async def estudiante_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

    @discord.ui.button(
        label="Visitante", 
        style=discord.ButtonStyle.secondary, 
        emoji="👋", 
        custom_id="btn_visitor_verify" # Explicit custom_id
    )
    async def visitante_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        guest_role = guild.get_role(GUEST_ROLE_ID)
        
        if guest_role:
            try:
                await interaction.user.add_roles(guest_role)
                embed = discord.Embed(
                    title="✅ Acceso de Visitante",
                    description="Se te ha asignado el rol de **Visitante**.",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("No tengo permisos para dar el rol.", ephemeral=True)
        else:
            await interaction.response.send_message("El rol de visitante no está configurado.", ephemeral=True)

# --- BOT MAIN SETUP ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True 

        super().__init__(
            command_prefix="!", 
            intents=intents,
            activity=discord.Game(name="¡Hola! Soy Jaguabot, el bot de la PFLC."),
            status=discord.Status.online
        )

    async def setup_hook(self):
        # Register the view for persistence before syncing
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
    # Send the ephemeral message with the persistent view
    await interaction.response.send_message(embed=embed, view=ChoiceView(), ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como: {bot.user}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ CRITICAL ERROR: TOKEN variable not found in environment.")
    else:
        bot.run(TOKEN)
