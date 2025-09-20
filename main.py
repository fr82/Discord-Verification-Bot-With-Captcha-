import discord
import json
import random
import asyncio
import os
from captcha.image import ImageCaptcha
import base64
import tempfile
from discord.ext import commands

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

bottoken = "enter_token_here"
verification_in_progress = {}

@client.event
async def on_ready():
    print(f"{client.user.name} is online!")
    while True:
        servers_count = len(client.guilds)
        await client.change_presence(activity=discord.Game(name=f"Protecting {servers_count} servers"), status=discord.Status.idle)
        await asyncio.sleep(5)  # Sleep for 5 seconds before updating again



@client.event
async def on_guild_join(guild):
    try:
        owner = guild.owner
        await owner.send("Greetings, thank you for inviting SenseLabs! Use `!setup` to easily set up the verification process in your server.")
        print(f"Sent a message to the owner of {guild.name}")
    except Exception as e:
        print(f"Failed to send a message to the owner of {guild.name}: {e}")


@client.event
async def on_member_join(member):
    try:
        with open(f'data/{member.guild.id}.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"The bot has not been set up for server {member.guild.name}.")
        return

    unverified_role_id = data.get('unverified_role_id')

    if unverified_role_id:
        role = discord.utils.get(member.guild.roles, id=unverified_role_id)
        if role:
            await member.add_roles(role)
            print(f"Assigned unverified role to {member.display_name} in server {member.guild.name}.")
        else:
            print(f"Unverified role not found in server {member.guild.name}.")
    else:
        print(f"Unverified role ID not found for server {member.guild.name}.")

    await member.send(f"Welcome to {member.guild.name}! Please run `!verify` to access the rest of the server.")

@client.command()
async def setup(ctx):
    if ctx.author.guild_permissions.administrator:
        if os.path.exists(f'data/{ctx.guild.id}.json'):
            await ctx.send("The server has already been set up. Use `!reset` command to reset data.")
            return
        
        await ctx.send("Please provide the ID of the 'Verified' role:")
        try:
            verified_role_id_msg = await client.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
            verified_role_id = int(verified_role_id_msg.content)

            await ctx.send("Please provide the ID of the 'Unverified' role:")
            unverified_role_id_msg = await client.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
            unverified_role_id = int(unverified_role_id_msg.content)

            await ctx.send("Please provide the ID of the verified channel:")
            verified_channel_id_msg = await client.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
            verified_channel_id = int(verified_channel_id_msg.content)

            guild_id = ctx.guild.id
            data = {'verified_role_id': verified_role_id, 'unverified_role_id': unverified_role_id, 'verified_channel_id': verified_channel_id}
            with open(f'data/{guild_id}.json', 'w') as f:
                json.dump(data, f)
            await ctx.send("Setup completed successfully!")
        except ValueError:
            await ctx.send("Invalid ID provided. Setup failed.")
        except asyncio.TimeoutError:
            await ctx.send("Setup timed out.")
    else:
        await ctx.send("Only administrators can execute this command.")

@client.command()
async def reset(ctx):
    if ctx.author.guild_permissions.administrator:
        if os.path.exists(f'data/{ctx.guild.id}.json'):
            os.remove(f'data/{ctx.guild.id}.json')
            await ctx.send("Data reset successful! You can now run the `!setup` command again.")
        else:
            await ctx.send("No data has been found to reset.")
    else:
        await ctx.send("Only administrators can execute this command.")

def generate_captcha():
    fontchoice = random.choice(["lovedays.ttf", "babyplums.ttf", "point.ttf", "avil.ttf", "corner.ttf"])
    image = ImageCaptcha(width=280, height=90, fonts=[fontchoice])

    CAPTEXT = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    captcha_text = ''.join(random.choices(CAPTEXT, k=5))  # Using random.choices for simplicity

    # Generate the image of the given text
    data = image.generate(captcha_text)

    # Read image file and encode it as base64
    img = data.getvalue()
    base64_encoded_img = base64.b64encode(img).decode('utf-8')

    # Prepare JSON response
    response_data = {
        "captcha_text": captcha_text,
        "captcha_image_base64": base64_encoded_img
    }

    return response_data


@client.command()
async def verify(ctx):
    # Initialize verification_in_progress dictionary if not already initialized
    if 'verification_in_progress' not in globals():
        globals()['verification_in_progress'] = {}

    # Check if the user already has a verification task in progress
    if ctx.author.id in verification_in_progress and verification_in_progress[ctx.author.id]:
        await ctx.send("You already have a verification task in progress.")
        return

    verification_in_progress[ctx.author.id] = True

    try:
        with open(f'data/{ctx.guild.id}.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        await ctx.send("The server owner has not set up the bot yet, please tell them to run the `!setup` command.")
        del verification_in_progress[ctx.author.id]
        return
    except json.JSONDecodeError:
        await ctx.send("There was an issue loading data from `data.json`. Please contact the bot owner.")
        del verification_in_progress[ctx.author.id]
        return

    verified_role_id = data.get('verified_role_id')
    unverified_role_id = data.get('unverified_role_id')
    verified_channel_id = data.get('verified_channel_id')

    if not all([verified_role_id, unverified_role_id, verified_channel_id]):
        await ctx.send("The server owner has not set up the bot correctly, please tell them to run the `!setup` command.")
        del verification_in_progress[ctx.author.id]
        return

    if ctx.message.author.guild_permissions.administrator:
        await ctx.send("This command cannot be used by administrators.")
        del verification_in_progress[ctx.author.id]
        return

    if discord.utils.get(ctx.author.roles, id=unverified_role_id) is None:
        await ctx.send("You need to have the unverified role to use this command. Try rejoining the server so the bot will automatically give you the `unverified` role.")
        del verification_in_progress[ctx.author.id]
        return

    if ctx.channel.id != verified_channel_id:
        await ctx.send("You can only verify in the specified channel.")
        del verification_in_progress[ctx.author.id]
        return

    message = await ctx.send(f"<@{ctx.author.id}> The Captcha has been sent to your DM's.")

    captcha_data = generate_captcha()
    captcha_text = captcha_data["captcha_text"]
    captcha_image_base64 = captcha_data["captcha_image_base64"]

    # Save the captcha image to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        temp_file.write(base64.b64decode(captcha_image_base64))
        filename = temp_file.name

    # Send the captcha image as a file attachment
    with open(filename, "rb") as f:
        file = discord.File(f)
        embed = discord.Embed(title="Solve the following captcha:")
        dm_message = await ctx.author.send(embed=embed)
        print(f"Captcha solution for {ctx.author.name} is {captcha_text}")
        await ctx.author.send(file=file)


    attempts = 3
    while attempts > 0:
        try:
            msg = await client.wait_for('message', check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel), timeout=60)
            if msg.content.lower() == captcha_text.lower():
                role = discord.utils.get(ctx.guild.roles, id=verified_role_id)
                if role:
                    await ctx.author.add_roles(role)
                    await ctx.author.remove_roles(discord.utils.get(ctx.guild.roles, id=unverified_role_id))
                    await ctx.author.send("**Captcha solved!** You have been verified.")
                    del verification_in_progress[ctx.author.id]
                    os.remove(filename)  # Remove the temporary file after verification
                    return
                else:
                    await ctx.author.send("Role not found. Please contact the server owner to correctly setup the bot.")
                    del verification_in_progress[ctx.author.id]
                    os.remove(filename)  # Remove the temporary file
                    return
            else:
                attempts -= 1
                if attempts > 0:
                    await ctx.author.send(f"Incorrect captcha. You have {attempts} attempts left. Try again.")
                else:
                    await ctx.author.send("Incorrect captcha. You have used all your attempts.")
        except asyncio.TimeoutError:
            await ctx.author.send("Time's up! You took too long to solve the captcha.")
            del verification_in_progress[ctx.author.id]
            os.remove(filename)  # Remove the temporary file
            return

    await ctx.send("Verification failed. You have used all your attempts.")
    del verification_in_progress[ctx.author.id]
    os.remove(filename)  # Remove the temporary file


client.run(f"{bottoken}")