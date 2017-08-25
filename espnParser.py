# -*- coding: utf-8 -*-
import sys
from lxml import html
from bs4 import BeautifulSoup
import requests
import argparse
import json
import re
import datetime
import urlparse

base_url = 'http://espndeportes.espn.com/'
fouls_committed = 0
fouls_committed_home = 1
fouls_committed_away = 5
labels = ['fouls', 'yellow_cards', 'red_cards', 'off_sides', 'corners', 'saves']


def parseDate(date):
    if date is not None:

        print (date)
        darr = ''
        if '/' in date:
            darr = date.split('/')
        elif '-' in date:
            darr = date.split('-')
        return darr[2] + darr[0] + darr[1]

def getMatchResult(score):
    if score[0] > score[1]:
        return ["Win", "Loss"]
    elif score[1] > score[0]:
        return ["Loss", "Win"]
    else:
        return ["tie", "tie"]

def getFTR(homeResult):
    if homeResult == 'Win':
        return 'H'
    elif homeResult == 'Loss':
        return 'A'
    else:
        return 'D'

def parseScheduleContainer(date):
    scheduleContainer = getPageScheduleContainer(date)

    matches = {}
    currentDate = ""
    for content in scheduleContainer[0].contents:

        # Match day, 00 month
        if re.match(".+,\s[0-3][0-9]\s.+", content.text):
            currentDate = content.text
        else:
            teams = content.find_all("tr", {"class": ["odd", "even"]})
            if len(teams) > 0:
                matches[currentDate] = parseMatch(teams)

    return matches

def parseMatch(lines):
    matches = []
    for line in lines:
        try:
            print line.contents[0].find_all("a", {"class": "team-name"})[0].find_all("span")[0].text + ' ' + \
                  line.contents[0].find_all("span", {"class": "record"})[0].find_all("a")[0].text + ' ' + \
                  line.contents[1].find_all("a", {"class": "team-name"})[0].find_all("span")[0].text

            home = line.contents[0].find_all("a", {"class": "team-name"})[0].find_all("span")[0].text
            away = line.contents[1].find_all("a", {"class": "team-name"})[0].find_all("span")[0].text
            score = line.contents[0].find_all("span", {"class": "record"})[0].find_all("a")[0].text.split(' - ')
            stats_link = line.contents[2].contents[0].attrs['href']

            h_stats, a_stats = getStatsContainer(urlparse.urljoin(base_url, stats_link))

            homeRes, awayRes = getMatchResult(score)


            if len(score) > 1:
                gameObj = {'home': {'name': home, 'score': score[0], 'result': homeRes, 'stats' : h_stats },
                           'away': {'name': away, 'score': score[1], 'result': awayRes, 'stats' : a_stats }}
            else:
                gameObj = {'home': {'name': home, 'score': 0, 'result': "tie", 'stats' : h_stats},
                           'away': {'name': away, 'score': 0, 'result': "tie", 'stats' : a_stats}}

            matches.append(gameObj)
        except:
            e = sys.exc_info()[0]
            print "There was a problem!"
            print e
    return matches


def getSoup(url):
    r = requests.get(url)

    soup = BeautifulSoup(r.content, "lxml")

    return soup

def getStatsContainer(url):
    soup = getSoup(url)

    stats = soup.findAll("table")

    label = 0
    h_stats = []
    a_stats = []
    for row in stats[0].findAll("tr")[1:]:

        home = row.contents[fouls_committed_home].contents[fouls_committed]
        away = row.contents[fouls_committed_away].contents[fouls_committed]

        h_stats.append(home)
        a_stats.append(away)
        #print (labels[label] + " \t home: " + home + ", away: " + away)
        label += 1

    return (h_stats, a_stats)


def getPageScheduleContainer(date):
    if date is None:
        return None
    date = parseDate(date)
    url =  urlparse.urljoin(base_url, '/futbol/fixtures/_/fecha/' + date + '/liga/mex.1')
    print 'fetching data from...'
    print url

    soup = getSoup(url)

    scheduleContainer = soup.findAll("div", {"id" : "sched-container"})

    return scheduleContainer

def writeMatchesToFile(date):
    lines = getPageScheduleContainer(date)

    matches = []
    for line in lines:
        home = cleanUpTeamName(line.contents[0].find_all("a", {"class": "team-name"})[0].find_all("span")[0].text) + ','
        score = line.contents[0].find_all("span", {"class": "record"})[0].find_all("a")[0].text + ','
        away = cleanUpTeamName(
            line.contents[1].find_all("a", {"class": "team-name"})[0].find_all("span")[0].text) + ',\n'
        match = home + score + away

        print match
        matches.append(match)

    writeToFile(matches)

def writeToFile(lines):
    file = 'matches.txt'
    with open(file, 'w') as f:
        for line in lines:
            print line
            f.write(line.encode('utf8'))
    print 'Information saved to ' + file

def writeToJsonFile(matches, outputName):
    with open(outputName + ".json", "w") as outfile:
        json.dump(matches, outfile)

def toCSVDataFormat(data):
    features = 'date, home, away, FTR, home_score, away_score, h_fouls, h_yellow_cards, h_red_cards, h_off_sides, ' \
               'h_corners, h_saves, a_fouls, a_yellow_cards, a_red_cards, a_off_sides, a_corners, a_saves\n'
    delim = ','
    for date, matches in data.items():
        for match in matches:
            homeResult = match['home']['result']
            awayResult = match['away']['result']

            features += date.replace(',', '') + delim + cleanUpTeamName(match['home']['name']) + delim + cleanUpTeamName(match['away']['name']) + \
                   delim + getFTR(homeResult) + delim + homeResult + delim + awayResult
            for stat in match['home']['stats']:
                features += delim + stat
            for stat in match['away']['stats']:
                features += delim + stat
            features += '\n'

    return features

def writeToCSV(data, outputName):
    d = toCSVDataFormat(data)
    with open(outputName + '.csv','wb') as file:
        for line in d:
            file.write(line.encode('ascii', 'ignore'))

# Needed for some unicode characters from mexican teams
def cleanUpTeamName(teamName):
    if not teamName.isalpha():
        if teamName.startswith('Q'):
            return 'Queretaro'
        if teamName.startswith('L'):
            return 'Leon'
    return teamName


d = "04/02/2016"  # input("Date of the page you want parsed, is the following format mm/dd/yyyy\n")


def parseInRange(startDate="01/01/2017", endDate="12/31/2017"):
    matches = {}

    sDate = startDate.split("/")
    eDate = endDate.split("/")
    startDate = datetime.date(int(sDate[2]), int(sDate[0]), int(sDate[1]))
    endDate = datetime.date(int(eDate[2]), int(eDate[0]), int(eDate[1]))

    delta = datetime.timedelta(days=1)
    while startDate <= endDate:
        day = startDate.strftime("%m/%d/%Y")
        matches.update(parseScheduleContainer(day))
        startDate += delta

    print str(startDate).split(',')
    writeToJsonFile(matches, "data-" + str(startDate).encode('ascii', 'ignore') + "_to_" + str(endDate))
    writeToCSV(matches, "data-" + str(startDate) + "_to_" + str(endDate))
    return matches


parseInRange("04/15/2017", "04/15/2017")

# Parse a 2017's
#parseInRange()

'''
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--date1", help="increase output verbosity")
args = parser.parse_args()
if args.verbosity:
    print "verbosity turned on"
'''

''' REMOVE THIS WHEN I WANT TO USE ON IT'S OWN 
parser = argparse.ArgumentParser()
parser.add_argument("date", help="Date of the page you want parsed, is the following format mm/dd/yyyy")
parser.add_argument("--Y", help="Year")

args = parser.parse_args()

print len(args)
#parse(args.date)
#print args.date
parseInRange(args.date)
#writeMatchesToFile(args.date)
'''
#cleanUpTeamName('Querétaro')

