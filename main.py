import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
ROL_POLICIA = "Los Angeles Police Departament"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ BASE DE DATOS ------------------
conn = sqlite3.connect("dni_rp.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS dni (
    user_id INTEGER PRIMARY KEY,
    nombre TEXT,
    apellido TEXT,
    edad TEXT,
    trabajo TEXT,
    nacionalidad TEXT,
    rasgos TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS delitos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    delito TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ordenes (
    user_id INTEGER PRIMARY KEY,
    activa INTEGER
)
""")

conn.commit()

# ------------------ EVENTO READY ------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

# ------------------ FORMULARIO DNI ------------------
class DNIForm(discord.ui.Modal, title="Crear DNI"):
    nombre = discord.ui.TextInput(label="Nombre")
    apellido = discord.ui.TextInput(label="Apellido")
    edad = discord.ui.TextInput(label="Edad")
    trabajo = discord.ui.TextInput(label="Trabajo actual")
    nacionalidad = discord.ui.TextInput(label="Nacionalidad")
    rasgos = discord.ui.TextInput(label="Rasgos físicos")

    async def on_submit(self, interaction: discord.Interaction):
        cursor.execute(
            "REPLACE INTO dni VALUES (?,?,?,?,?,?,?)",
            (
                interaction.user.id,
                self.nombre.value,
                self.apellido.value,
                self.edad.value,
                self.trabajo.value,
                self.nacionalidad.value,
                self.rasgos.value
            )
        )
        conn.commit()
        await interaction.response.send_message(
            "✅ **DNI creado correctamente**",
            ephemeral=True
        )

# ------------------ COMANDOS CIVILES ------------------
@bot.tree.command(name="creardni", description="Crear tu DNI de rol")
async def creardni(interaction: discord.Interaction):
    await interaction.response.send_modal(DNIForm())

@bot.tree.command(name="midni", description="Ver tu DNI")
async def midni(interaction: discord.Interaction):
    cursor.execute("SELECT * FROM dni WHERE user_id=?", (interaction.user.id,))
    data = cursor.fetchone()

    if not data:
        await interaction.response.send_message("❌ No tienes DNI", ephemeral=True)
        return

    embed = discord.Embed(
        title="🪪 Documento de Identidad",
        color=discord.Color.blue()
    )
    embed.add_field(name="Nombre", value=data[1])
    embed.add_field(name="Apellido", value=data[2])
    embed.add_field(name="Edad", value=data[3])
    embed.add_field(name="Trabajo", value=data[4])
    embed.add_field(name="Nacionalidad", value=data[5])
    embed.add_field(name="Rasgos", value=data[6])
    embed.set_footer(text="RP serio")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="borrardni", description="Borrar tu DNI")
async def borrardni(interaction: discord.Interaction):
    cursor.execute("DELETE FROM dni WHERE user_id=?", (interaction.user.id,))
    cursor.execute("DELETE FROM delitos WHERE user_id=?", (interaction.user.id,))
    cursor.execute("DELETE FROM ordenes WHERE user_id=?", (interaction.user.id,))
    conn.commit()
    await interaction.response.send_message("🗑️ DNI borrado", ephemeral=True)

# ------------------ COMANDOS POLICIA ------------------
def es_policia(member: discord.Member):
    return any(rol.name == ROL_POLICIA for rol in member.roles)

@bot.tree.command(name="revisardni", description="Revisar DNI (LAPD)")
async def revisardni(interaction: discord.Interaction, usuario: discord.Member):
    if not es_policia(interaction.user):
        await interaction.response.send_message("❌ No eres policía", ephemeral=True)
        return

    cursor.execute("SELECT * FROM dni WHERE user_id=?", (usuario.id,))
    data = cursor.fetchone()

    if not data:
        await interaction.response.send_message("❌ Ese usuario no tiene DNI", ephemeral=True)
        return

    cursor.execute("SELECT delito FROM delitos WHERE user_id=?", (usuario.id,))
    delitos = cursor.fetchall()

    cursor.execute("SELECT activa FROM ordenes WHERE user_id=?", (usuario.id,))
    orden = cursor.fetchone()

    embed = discord.Embed(
        title="🚓 Registro Policial",
        color=discord.Color.red()
    )
    embed.add_field(name="Nombre", value=f"{data[1]} {data[2]}")
    embed.add_field(name="Edad", value=data[3])
    embed.add_field(name="Trabajo", value=data[4])
    embed.add_field(
        name="Delitos",
        value="\n".join(d[0] for d in delitos) if delitos else "Ninguno",
        inline=False
    )
    embed.add_field(
        name="Orden de búsqueda",
        value="✅ ACTIVA" if orden and orden[0] == 1 else "❌ No"
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="agregardelito", description="Agregar delito (LAPD)")
async def agregardelito(interaction: discord.Interaction, usuario: discord.Member, delito: str):
    if not es_policia(interaction.user):
        await interaction.response.send_message("❌ No eres policía", ephemeral=True)
        return

    cursor.execute("INSERT INTO delitos (user_id, delito) VALUES (?,?)", (usuario.id, delito))
    conn.commit()
    await interaction.response.send_message("✅ Delito agregado", ephemeral=True)

@bot.tree.command(name="ordenbusqueda", description="Activar o quitar orden (LAPD)")
async def ordenbusqueda(interaction: discord.Interaction, usuario: discord.Member, estado: str):
    if not es_policia(interaction.user):
        await interaction.response.send_message("❌ No eres policía", ephemeral=True)
        return

    activa = 1 if estado.lower() == "activar" else 0
    cursor.execute("REPLACE INTO ordenes VALUES (?,?)", (usuario.id, activa))
    conn.commit()

    await interaction.response.send_message(
        f"⚠️ Orden de búsqueda {'activada' if activa else 'quitada'}",
        ephemeral=True
    )

# ------------------ INICIAR BOT ------------------
bot.run(TOKEN)
