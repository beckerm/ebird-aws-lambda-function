import json
import urllib.request
import os
from datetime import datetime
from collections import defaultdict
import calendar
import sys
import re
import boto3
from botocore.exceptions import ClientError


def send_email(the_sender, the_recipient, the_subject, the_body_html):

    SENDER = the_sender
    RECIPIENT = ", ".join(the_recipient)
    AWS_REGION = "us-west-2"
    SUBJECT = the_subject
    BODY_HTML = the_body_html
    CHARSET = "UTF-8"

    client = boto3.client('ses', region_name=AWS_REGION)

    try:
        response = client.send_email(
            Destination={'ToAddresses': the_recipient},
            Message={'Body': {'Html': {'Charset': CHARSET, 'Data': BODY_HTML, }, },
                     'Subject': {'Charset': CHARSET, 'Data': SUBJECT, }, },
            Source=SENDER,
        )

    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Ok!")


def xstr(s):
    if s is None:
        return ''
    return str(s)


def get_bird_data(x_lng, x_lat, x_days, x_dist):

    bird_list = []
    birds = []
    location_bird_list = defaultdict(list)
    ebird_key = os.environ['ebird_key']

    days = {
        0: 'Mon',
        1: 'Tue',
        2: 'Wed',
        3: 'Thu',
        4: 'Fri',
        5: 'Sat',
        6: 'Sun'
    }

    geo_url = 'https://ebird.org/ws2.0/data/obs/geo/recent?lng=' + x_lng + '&lat=' + x_lat + '&dist=' + \
        x_dist + '&back=' + x_days + '&maxResults=1000&fmt=json&includeProvisional=true&key=' + ebird_key

    try:
        data = json.load(urllib.request.urlopen(geo_url))
    except urllib.request.HTTPError as e:
        print ('Error: ', e)

    for i in data:
        year, month, day = (int(x) for x in str(i.get('obsDt')[:10]).split('-'))
        dow = calendar.weekday(year, month, day)
        new_date = str(month) + '/' + str(day) + '/' + str(year)
        bird_list.append([str(i.get('comName')), str(i.get('howMany')), new_date +
                          '  (' + str(days.get(dow)) + ')', str(i.get('locName'))])

    bird_list.sort()

    for s in bird_list:
        location_bird_list[s[3]].append(s)

    def html_wrap_location(loc):
        w = '<tr><td><b><u>' + loc + '</u></b></td></tr>'
        return w

    def html_wrap_bird(bird, qty, day):
        w = "<tr><td>" + bird + "  (" + qty + ")</td><td align=\"left\">" + day + "</td></tr>"
        return w

    html_table = "<html><table style=\"font-family:arial\"  width=\"875\">"
    html_row = ''
    empty_row = '<tr><td></td><td></td><td></td></tr>'

    for l, birds in location_bird_list.items():
        html_row = html_wrap_location(l)

        for b in birds:
            html_row = html_row + html_wrap_bird(str(b[0]).strip(), str(b[1]), str(b[2]))

        html_table = html_table + html_row + empty_row + empty_row

    html_table = html_table + "</table></html>"

    return html_table


def lambda_handler(event, context):
    lng = event["longitude"]
    lat = event["latitude"]
    days = event["daysback"]
    dist = event["distance"]
    region = event["region"]
    send_to = event["recipients"]

    subject_line = 'Bird Sightings ' + region + ' Last ' + days + ' Day(s) ' + dist + ' Mile Radius'

    bird_msg = get_bird_data(lng, lat, days, dist)
    send_email("Bird Nerd <birder@gmail.com>", send_to, subject_line, bird_msg)
