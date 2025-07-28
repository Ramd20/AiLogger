import discord
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

# configurations

SHEET_NAME = "Resale Log"  # Name of your Google Sheet
openai.api_key = os.getenv("OPENAI_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# google sheets set up
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# discord bot set up
intents = discord.Intents.default()
intents.message_content = True
client_bot = discord.Client(intents=intents)

@client_bot.event
async def on_ready():
    print(f"✅ Logged in as {client_bot.user}")

@client_bot.event
async def on_message(message):
    if message.author == client_bot.user:
        return

    if message.content.startswith("!log "):
        entry = message.content[5:]

        if "today" in entry:
            entry = entry.replace("today", datetime.now().strftime("%Y-%m-%d"))

        print("Received", entry)

        prompt = f"""
Extract the following purchase log into a JSON with these fields:
- product
- quantity
- total price (not unit price)
- retailer (store name or abbreviation like WM = Walmart, AMZ = Amazon, etc.)
- card (if mentioned)
- date (in YYYY-MM-DD format if mentioned)
- tax free (default no)

Requirements:
- "price" must be the TOTAL price for all units (e.g., 3 items at $10 = 30).
- Use numbers only (no $ or commas) for quantity and price.
- If a field is not mentioned, set its value to unknown.
- If retailer is abbreviated (e.g. WM, AMZ, BBY), return full name.
- Return only valid JSON (no markdown, no commentary).

Input: "{entry}"

Output format:
{{"product": "...", "quantity": ..., "price": ..., "retailer": "...", "card": "...", "date": "...", "tax free": "..."}}
"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            result = eval(response['choices'][0]['message']['content'])  # For now, trust GPT to return JSON

            sheet.append_row([
                result["date"],
                result["product"],
                result["quantity"],
                result["price"],
                result["retailer"],
                result["card"],
                result["tax free"]
            ])

            await message.channel.send(
                f"✅ Logged: {result['quantity']} {result['product']} for {result['price']} at {result['retailer']} on {result['date']} with {result['card']}"
            )

        except Exception as e:
            await message.channel.send(f"❌ Error: {str(e)}")

client_bot.run(DISCORD_TOKEN)
