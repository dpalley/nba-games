from datetime import datetime, timedelta
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import sys
import bs4

# This scope allows read/write access to Google Calendar information.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def help():
    print('This script parses the ESPN web site for the schedule of an NBA team.')
    print('Currently, the script parses the Houston Rockets schedule, but that can ')
    print('be modified by the user.\n')
    print('The user is presented with the date, time, and location of the upcoming opponents.\n')
    print('The user may enter a maximum number of games to review on the command line. Simply')
    print('add a space and a number after typing "python nba.py".\n')
    print('To review the next 5 games, enter:')
    print('\npython nba.py 5\n')
    print('Not including a number will allow the user to review all upcoming games.\n')
    print('After the information for each game is presented, the user is given ')
    print('the option to add the event to their Google Calendar, ignore the')
    print('information, or exit out of the script.')

def get_calendar_service():
    """This code is lifted from the Google Calendar Python Quickstart page.
    Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    return service


def get_schedule():
    '''Returns a list of HTML 'tr' blocks, each block representing an individual
    game and containing multiple 'td' blocks.
    The individual 'td' elements contain the schedule info (opponent, date, etc.).
    Modify the URL for your favorite NBA team.
    '''
    team = requests.get('https://www.espn.com/nba/team/schedule/_/name/hou').text
    soup = bs4.BeautifulSoup(team, 'html.parser')
    games = soup.find_all('tr', class_='Table__TR')
    return games


def start_stop(date, time):
    ''' Takes a date and start time, adds 2 hours to set and end time, and
    formats the start and end times into a format expected by Google Calendar.
    input day format:         'Mon, Oct 28'
    input time format:        '8:00 PM'
    expected output format:   '2019-10-28T20:00:00'
    '''

    months = {'Oct':10,'Nov':11,'Dec':12,'Jan':1,'Feb':2,'Mar':3,'Apr':4}

    month = months[date[5:8]]
    if month in (1, 2, 3, 4):
        year = 2020
    elif month in (10, 11, 12):
        year = 2019
    else:
        raise ValueError('Invalid month information')
    day = int(date[9:])
    colon = time.find(':')
    hours = int(time[:colon])
    minutes = int(time[colon+1:colon+3])
    if time[-2:] == 'PM':
        hours += 12

    start = datetime(year, month, day, hours, minutes)
    end = (start + timedelta(hours=2)).isoformat()
    start = start.isoformat()

    return (start, end)


def get_info(televised, tickets):
    if televised:
        return f'On {televised}. {tickets}'
    else:
        return f'Not televised. {tickets}'


def add_to_calendar(place, start, stop, info):

   service = get_calendar_service()

   service.events().insert(calendarId='primary',
       body={
           "summary": place,
           "description": info,
           "start": {"dateTime": start, "timeZone": 'America/Chicago'},
           "end": {"dateTime": stop, "timeZone": 'America/Chicago'},
           }
       ).execute()


if __name__ == '__main__':

    # import pdb; pdb.set_trace()
    if len(sys.argv) == 1:
        games_to_review = 82
    elif sys.argv[1] == '-h' or sys.argv[1] == '--help':
        help()
        sys.exit()
    try:
        games_to_review = int(sys.argv[1])
    except:
        print('The parameter must either be an integer or "-h".\n')
        sys.exit()

    print('For each game, enter: "y" to add the game to your Calendar,')
    print('"q" to quit out of the script, or any other key to skip that game.')

    # service = get_calendar_service()
    games = get_schedule()

    games_reviewed = 0
    for game in games:
        game_info = game.find_all('td', class_='Table__TD') # elements containing game info
        if len(game_info) > 5:  # completed game has additional info, skip
            continue

        game_info = [item.text for item in game_info]
        date, location, time, televised, tickets = game_info
        if date == 'Date':   # header row, skip
            continue

        print(f'\nPlaying {location} on {date} at {time}')
        if time == 'LIVE':
            print("Game is live - won't add to calendar.")
            continue
        print(get_info(televised, tickets))
        response = input('"y" to add, "q" to quit, or any other key to skip: ').lower()

        if response == 'q':
            break
        elif response == 'y':
            start_time, stop_time = start_stop(date, time)
            add_to_calendar(location, start_time, stop_time, get_info(televised, tickets))
        games_reviewed += 1
        if games_reviewed >= games_to_review:
            print('You have reviewed {games_to_review} games. Exiting ...\n')
            break
