from steam import Steam
from decouple import config
import json
import requests
from bs4 import BeautifulSoup
import random
import os


class Game:
    def __init__(self, name, id, score):
        self.name = name
        self.id = id
        self.score = score

    def PrintGame(self):
        print(f"Game: {self.name}\nID: {self.id}\nScore: {self.score}\n")


def GameSort(games):
    newGames = []
    while len(games) > 0:
        maxscore = games[0].score
        midx = 0
        for i in range(len(games)):
            if games[i].score > maxscore:
                maxscore = games[i].score
                midx = i
        newGames.append(games.pop(midx))
    return newGames


def SaveResultsToFile(games, fileName):
    f = open(fileName, "w")
    for i in range(len(games)):
        line = f"{i+1}: {games[i].name}  https://store.steampowered.com/app/{games[i].id}/\n"
        f.write(line)
    f.close()


def GetSteamTags(appId):
    url = f'https://store.steampowered.com/app/{appId}/'
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        tagsContainer = soup.find('div', {'class': 'glance_tags'})
        if tagsContainer:
            tags = [tag.text.strip() for tag in tagsContainer.find_all('a')]
            return tags
        else:
            return None
    else:
        print(f"Failed to fetch the page. Status Code: {response.status_code}")
        return None


def PopulateTagsDict(hours, appIds):
    tagsDict = {}
    hidx = -1
    for id in appIds:
        hidx += 1
        tags = GetSteamTags(id)
        if tags:
            for tag in tags:
                if tag in tagsDict:
                    tagsDict[tag] += hours[hidx]
                else:
                    tagsDict[tag] = hours[hidx]
        else:
            print(f"Failed to retrieve tags for game {id}.")
    return tagsDict


def PrintDict(dict):
    pretty = json.dumps(dict, indent=4)
    print(pretty)


def GetRandomGame():
    url = 'http://api.steampowered.com/ISteamApps/GetAppList/v2/'
    response = requests.get(url)

    if response.status_code == 200:
        appList = response.json()['applist']['apps']
        randomGame = random.choice(appList)
        return [randomGame['name'], randomGame['appid']]
    else:
        print(f"Failed to fetch app list. Status Code: {response.status_code}")
        return None


def GetScoresFromRandomGames(heuristic, size, appIds):
    games = []
    for x in range(size):
        randomGame = GetRandomGame()
        if randomGame == None:
            x-= 1
            continue
        if randomGame[1] in appIds:
            x-= 1
            continue
        score = 0
        tags = GetSteamTags(randomGame[1])
        if tags == None:
            continue
            x-= 1
        for tag in tags:
            if tag in heuristic:
                score += heuristic[tag]
            else:
                score -= 5
        games.append(Game(randomGame[0], randomGame[1], score))
    return games


def PrintTopGames(games, times, steamid):
    if len(games) < times:
        rounds = len(games)
    else:
        rounds = times
    games = GameSort(games)
    print(f"Top {rounds} reccomendations:")
    for j in range(rounds):
        print(f"{j+1}: {games[j].name}")
    response = input("Save results? [Y/n]: ")
    if response == "Y" or response == "y":
        name = steamid + ".txt"
        SaveResultsToFile(games, name)
        
    
def GetTagsWeight(steam, steamid):
    # arguments: steamid
    user = steam.users.get_owned_games(steamid)
    PrintDict(user)
    print("Got user's owned games")
    appIds = [game.get("appid") for game in user.get("games", [])]
    minutes = [game.get("playtime_forever") for game in user.get("games", [])]
    hours = [time // 60 for time in minutes]
    twoweeks = [game.get("playtime_2weeks") for game in user.get("games", [])]

    for i in range(len(twoweeks)):
        if twoweeks[i] == None:
            twoweeks[i] = 0
        hours[i] += (twoweeks[i] // 60)

    print("Getting tag weights...")
    tagsDict = populateTagsDict(hours, appIds)
    print("Got all tag weights")
    response = input("Save weights to a json file? [Y/n]: ")

    if response == "Y" or response == "y":
        filePath = f"{steamid}.json"
        with open(filePath, 'w') as jsonFile:
            json.dump(tagsDict, jsonFile, indent=4)
        print(f"Data has been exported to {filePath}")
        
    return tagsDict    
       
def Reccomendation():
    KEY = config("STEAM_API_KEY")
    steam = Steam(KEY)

    steamidz = input("Enter steam id or skip for default(mine): ")
    if steamidz == "":
        steamid = "76561198260358525"
    else:
        steamid = steamidz
    
    gamesToReview = input("Enter number of games to search for or skip for default(100): ")
    if gamesToReview == "":
        gamesToReview = 100
    try:
        gamesToReview = int(gamesToReview)
    except:
        gamesToReview = 100

    top = input("Enter number of results to show or skip for default(10): ")
    if top == "":
        top = 10
    try:
        top = int(top)
    except:
        top = 10

    filePath = f"{steamid}.json"
    tagsDict = {}
    user = steam.users.get_owned_games(steamid)
    appIds = [game.get("appid") for game in user.get("games", [])]
    if os.path.exists(filePath):
        response = input("JSON file for this user detected. Use file? [Y/n]: ")
        if response == "Y" or response == "y":
            with open(filePath, 'r') as jsonFile:
                tagsDict = json.load(jsonFile)
        else:
            tagsDict = GetTagsWeight(steam, steamid)
    else:
        tagsDict = GetTagsWeight(steam, steamid)
    
    print("Searching for games...")
    games = GetScoresFromRandomGames(tagsDict, gamesToReview, appIds)
    PrintTopGames(games, top, steamid)




Reccomendation()
