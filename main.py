import discord
import asyncio
import json
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import pandas as pd
import json
from datetime import datetime, timedelta
import re
import time

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

tracked_users = {}

def save_tracked_users():
    with open('tracked_users.json', 'w') as f:
        json.dump(tracked_users, f)

def load_tracked_users():
    try:
        with open('tracked_users.json', 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                return {}
    except FileNotFoundError:
        return {}
    except json.decoder.JSONDecodeError:
        return {}

def generate_chart(data, username):  
    data["data"] = True

    data_dict = [json.loads(item) for item in data["result"]]
    df = pd.DataFrame(data_dict)

    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')

    plt.figure(figsize=(10, 6))

    plt.plot(df['date'], df['diamants'], label='Diamants')
    plt.plot(df['date'], df['patrimoine'], label='Richesse total')
    plt.plot(df['date'], df['classiques'], label='Classiques')
    plt.plot(df['date'], df['badges'], label='Valeur des badges')

    plt.xlabel('Date')
    plt.ylabel('Valeur')
    plt.title(f'Evolution de la richesse de {username}')  
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = "chart.png"
    plt.savefig(chart_path)
    plt.close()
    return chart_path

def get_graph_data(ids):
    url = f"https://www.habbocity.me/modules/center/action/inventory/ActionGraphicRichest.php?playerId={ids}"
    response = requests.get(url)
    graph_data = response.text
    return graph_data

def get_friend(ids):
    url = f"https://www.habbocity.me/modules/profile/friends/ModuleProfileFriends.php?playerId={ids}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    if soup.find(class_='moduleProfileFriendsUnavailableText') is not None:
        return "La liste d'amis de cet utilisateur est masquée."
    
    friend_names = soup.find_all(class_="moduleProfileFriendsPseudo")
    friend_list = '\n'.join(name.text for name in friend_names)
    return friend_list

def get_rich_class(ids):
    url = f"https://www.habbocity.me/modules/center/action/inventory/ActionCalcPrestigePosition.php?playerId={ids}"
    response = requests.get(url)
    class_rich = response.text
    return class_rich

def get_badges(username):
    url = f"https://www.habbocity.me/modules/profile/ModuleProfile.php?playerId=0&username={username}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    badge_container = soup.find(class_="moduleProfileLeftBadgesBox")
    if badge_container:
        badge_elements = badge_container.find_all(class_="moduleProfileLeftBadgesRounder")
        badges = []
        for badge_element in badge_elements:
            badge_img = badge_element.find("img")
            if badge_img:
                badge_title = badge_element.find(class_="moduleProfileLeftBadgesRounderInfoTitle").text.strip()
                badges.append(badge_title)
        return badges
    else:
        return None

def get_status(username):
    url = f"https://www.habbocity.me/modules/profile/ModuleProfile.php?playerId=0&username={username}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    status = soup.find(class_='moduleProfileUserBox').find_next('span').text
    return status

def get_auction_badges():
    url = "https://www.habbocity.me/modules/center/auction/badges/ModuleCenterAuctionBadges.php"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    badge_elements = soup.find_all(class_="moduleCenterAuctionBadgeBubble")
    badges = [element.find(class_="moduleCenterMAuctionRareTitle").text.strip() for element in badge_elements]
    return badges

def lookupu(username):
    url = f"https://www.habbocity.me/modules/profile/ModuleProfile.php?playerId=0&username={username}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    avatar_url = soup.find(class_='moduleProfileLeftBannerAvatar').img['src']
    statues =  soup.find(class_='moduleProfileUserBox').find_next('span').text
    richess = soup.find(class_='moduleProfileIconRichess').find_next('span').text
    ids =  soup.find(class_='moduleProfile').find_next('div').text
    respect = soup.find(class_='moduleProfileIconLike').find_next('span').text
    relation_status = soup.find(class_='moduleProfileIconHeart').find_next('span').text
    avatar_url1 = soup.find(class_='moduleProfileAvatar').img['src']
    vip_badge = soup.find(class_='moduleProfileUserFunction') is not None
    join_date = soup.find(class_='moduleProfileIconTime').find_next('span').text

    class_rich = get_rich_class(ids)
    friend_list = get_friend(ids)
    graph_data = get_graph_data(ids)
    data = json.loads(graph_data)
    chart_path = generate_chart(data, username)

    badges = get_badges(username)

    return avatar_url, avatar_url1, richess, respect, relation_status, statues, ids, class_rich, friend_list, chart_path, badges, vip_badge, join_date

async def check_user_status(username):
    previous_status = None
    connect_time = None
    mention_string = None  # Déplacez cette ligne en dehors de la boucle
    while True:
        user_status = get_status(username)
        
        if user_status == "En ligne" and previous_status != "En ligne":
            connect_time = datetime.now()
            snipers = [user_id for user_id, sniped_list in tracked_users.items() if username in sniped_list]
            if snipers:
                mention_string = ' '.join([f"<@{user_id}>" for user_id in snipers])
                await bot.get_channel(1238491949174886471).send(f"{mention_string} **{username}** vient de se connecter !")
        
        elif user_status != "En ligne" and previous_status == "En ligne":
            if connect_time:
                disconnect_time = datetime.now()
                playtime = disconnect_time - connect_time
                playtime_hours = playtime.seconds // 3600
                playtime_minutes = (playtime.seconds % 3600) // 60
                await bot.get_channel(1238491949174886471).send(f"{mention_string} **{username}** vient de se déconnecter, il a joué {playtime_hours} heures et {playtime_minutes} minutes !")
            snipers = [user_id for user_id, sniped_list in tracked_users.items() if username in sniped_list]
            if snipers:
                mention_string = ' '.join([f"<@{user_id}>" for user_id in snipers])
                await bot.get_channel(1238491949174886471).send(f"{mention_string} **{username}** vient de se déconnecter !")
        
        previous_status = user_status
        await asyncio.sleep(10)
        
async def check_auction_badges():
    tracked_badges = set()
    initial_check = True
    while True:
        try:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking auction page...")
            new_badges = get_auction_badges()
            if initial_check:
                tracked_badges.update(new_badges)
                initial_check = False
            else:
                for badge in new_badges:
                    if badge not in tracked_badges:
                        channel = bot.get_channel(1238942562262323260)
                        role = channel.guild.get_role(1238942701504696480)
                        await channel.send(f"<@&{role.id}> Un nouveau badge a été mis aux enchères : {badge}")
                        tracked_badges.add(badge)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Auction page check complete.")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] An error occurred while checking auction page: {str(e)}")
        
@bot.event
async def on_ready():
    print("Bot is ready!")
    bot.loop.create_task(check_auction_badges())
    
@bot.event
async def on_command(ctx):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {ctx.author.name} used '{ctx.command}' command")

@bot.command()
async def bot_help(ctx):
    help_message = "Voici la liste des commandes disponibles :\n"
    for command in bot.commands:
        help_message += f"**{command.name}**\n"
    await ctx.send(help_message)

@bot.command()
async def snipe(ctx, username):
    await ctx.send(f"Vous serez mentionné la prochaine fois que {username} se connecte.")
    
@bot.command()
async def track(ctx, username):
    if ctx.author.id not in tracked_users:
        tracked_users[ctx.author.id] = []

    if username in tracked_users[ctx.author.id]:
        await ctx.send("Vous trackez déjà ce joueur.")
    else:
        tracked_users[ctx.author.id].append(username)
        save_tracked_users()
        await ctx.send(f"Le joueur {username} est maintenant dans votre tracklist.")

        if len(tracked_users[ctx.author.id]) == 1:
            await check_user_status(username)
            
@bot.command()
async def untrack(ctx, username):
    if ctx.author.id in tracked_users:
        if username in tracked_users[ctx.author.id]:
            tracked_users[ctx.author.id].remove(username)
            save_tracked_users()
            await ctx.send(f"Le joueur {username} a été retiré de votre tracklist.")
        else:
            await ctx.send(f"Le joueur {username} n'est pas dans votre tracklist.")
    else:
        await ctx.send("Vous ne trackez actuellement aucun joueur.")

@bot.command()
async def staff(ctx):
    url = "https://www.habbocity.me/team"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        total_staff = 0
        checked_staff = 0

        staff_members = soup.find_all(class_="teamRightMembersBubble")

        embed = discord.Embed(
            title="Staff connectés...",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Staff connectés : {checked_staff}")
        message = await ctx.send(embed=embed)

        for member in staff_members:
            total_staff += 1
            username = member.find(class_="teamRightMembersPseudo").text
            online_status = member.find(class_="teamRightBubbleOffline")

            if online_status:
                status = "Hors ligne"
            else:
                status = "En ligne"
                checked_staff += 1
                embed.add_field(name=username, value=status, inline=False)
                await message.edit(embed=embed)
                embed.set_footer(text=f"Staff connectés : {checked_staff}")
                await message.edit(embed=embed)

    else:
        await ctx.send("Erreur lors de la récupération de la page")

@bot.command()
async def check(ctx, username):
    url = f"https://www.habbocity.me/modules/profile/ModuleProfile.php?playerId=0&username={username}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    status_span = soup.find(class_='moduleProfileUserBox').find_next('span')
    if status_span is None:
        await ctx.send(f"Failed to retrieve status for username '{username}'.")
        return
    
    status_text = status_span.text
    last_online_match = re.search(r'\d{2}-\d{2}-\d{4}', status_text)
    
    if last_online_match:
        last_online_date = datetime.strptime(last_online_match.group(), "%d-%m-%Y")
        one_year_ago = datetime.now() - timedelta(days=365)
        if last_online_date < one_year_ago:
            await ctx.send(f"The username '{username}' is requestable (offline since {last_online_match.group()}).")
        else:
            await ctx.send(f"The username '{username}' is not available.")
    else:
        await ctx.send(f"Failed to parse last online date for username '{username}'.")

@bot.command()
async def tracklist(ctx):
    if ctx.author.id in tracked_users and tracked_users[ctx.author.id]:
        embed = discord.Embed(
            title="Voici votre tracklist:",
            color=discord.Color.dark_gray()
        )
        for username in tracked_users[ctx.author.id]:
            user_status = get_status(username)
            if user_status == "En ligne":
                status_emoji = "🟢"
            else:
                status_emoji = "🔴"
            embed.add_field(name=f"{status_emoji} {username}", value="\u200b", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Vous ne trackez actuellement aucun joueur.")
        
@bot.command()
async def forcetrack(ctx, user_id: int, username):
    if ctx.author.id != 123980085836382208:
        await ctx.send("Vous n'avez pas la permission d'utiliser cette commande.")
        return

    if user_id not in tracked_users:
        tracked_users[user_id] = []

    if username in tracked_users[user_id]:
        await ctx.send("Ce joueur est déjà dans la track list de cet utilisateur.")
    else:
        tracked_users[user_id].append(username)
        save_tracked_users()
        await ctx.send(f"Le joueur {username} a été ajouté à la track list de l'utilisateur avec l'ID {user_id}.")

@bot.command()
async def lookup(ctx, name):
    username = name
    avatar_url, avatar_url1, richess, respect, relation_status, statues, ids, class_rich, friend_list, chart_path, badges, vip_badge, join_date = lookupu(username)
    
    status_emoji = "🟢" if statues == "En ligne" else "🔴"
    color = discord.Color.dark_gray()
    
    chart_file = discord.File(chart_path, filename="chart.png")

    embed = discord.Embed(
        title=f"{username}'s profile",
        url=f"https://www.habbocity.me/profil/{username}",
        color=color
    )
    embed.set_image(url="attachment://chart.png")
    embed.add_field(name="Richesse 🎁", value=f"{richess}")
    embed.add_field(name="Classement 💰", value=f"#{class_rich}")
    embed.add_field(name="Respect(s) 🧧", value=f"{respect}")
    if vip_badge:
        embed.add_field(name="VIP", value=":crown:")
    if badges:
        badge_list = ', '.join(badges)
        embed.add_field(name="Badges:", value=badge_list)
    embed.add_field(name="Relation 🎭", value=f"{relation_status}")
    embed.add_field(name="Status", value=f"{status_emoji} {statues}", inline=False)
    embed.add_field(name="Inscrit le :", value=f"{join_date}", inline=False)

    if friend_list.startswith("La liste d'amis de cet utilisateur est masquée."):
        embed.add_field(name="Friends:", value=friend_list)
    else:
        embed.add_field(name="Friends:", value=friend_list, inline=False)

    embed.set_author(name=f"Profile Lookup", url=f"https://www.habbocity.me/profil/{username}", icon_url=f"{avatar_url1}")

    embed.set_thumbnail(url=f"{avatar_url}")

    await ctx.send(file=chart_file, embed=embed)

bot.run('MTIzODA4ODQ5MjYwNTY0MDcwNA.G6hw7b.P2ed0B1ftU4n13wjdMUiw2DRRXRblwP-gNtVyU')