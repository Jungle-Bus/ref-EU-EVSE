#!/usr/bin/env python
# coding: utf-8

import json
import csv
import requests
from time import strftime, localtime

overpass_base_url = "http://overpass-api.de/api/interpreter?data="
overpass_params = """
[out:json][timeout:825];area(3602202162)->.searchArea;(node["amenity"="charging_station"](area.searchArea);way["amenity"="charging_station"](area.searchArea););out;>;out skel qt;
"""

overpass_requests = requests.get(overpass_base_url + overpass_params)

if not overpass_requests.ok:
    print("kapout : requête échouée") #TODO
    print(overpass_requests.status_code)
if not overpass_requests.json()['elements']:
    print("kapout : pas d'éléments") #TODO

elements = overpass_requests.json()['elements']
charging_stations = [elem for elem in elements if 'tags' in elem and 'amenity' in elem['tags'] and elem['tags']['amenity']=="charging_station"]

results_of_the_day = {}
results_of_the_day['total_number'] = len(charging_stations)
results_of_the_day['total_number_motorcar'] = len([elem for elem in charging_stations if 'motorcar' in elem['tags'] and elem['tags']['motorcar']=='yes'])
results_of_the_day['total_number_bicycle'] = len([elem for elem in charging_stations if 'bicycle' in elem['tags'] and elem['tags']['bicycle']=='yes'])
results_of_the_day['total_with_open_data_ref'] = len([elem for elem in charging_stations if 'ref:EU:EVSE' in elem['tags']])
results_of_the_day['total_with_fixme'] = len([elem for elem in charging_stations if 'fixme' in elem['tags'] or 'FIXME' in elem['tags']])
results_of_the_day['percentage_free'] = len([elem for elem in charging_stations if 'fee' in elem['tags'] and elem['tags']['fee']=='no'])*100.0 / len(charging_stations)

nb_places = len([elem for elem in charging_stations if 'capacity' not in elem['tags']])
tt = [elem for elem in charging_stations if 'capacity' in elem['tags']]
for elem in tt :
    try:
        nb_places += int(elem['tags']['capacity'])
    except ValueError:
        print('{} - {}/{}'.format(elem['tags']['capacity'], elem['type'],elem['id']))
        nb_places += 1

results_of_the_day['total_number_of_parking_spaces'] = nb_places

date_local = strftime("%Y-%m-%d %H:%M:%S", localtime())
results_of_the_day['datetime'] = date_local

print("{} éléments".format(results_of_the_day['total_number']))

print("{} éléments avec ref open data".format(results_of_the_day['total_with_open_data_ref']))

# récupérer la dernière version du fichier de stats
public_stats_url = "https://raw.githubusercontent.com/Jungle-Bus/ref-EU-EVSE/gh-pages/osm_stats.csv"
req = requests.get(public_stats_url)

with open ("output/osm_stats.csv", "w") as csv_out_file:
    csv_out_file.write(req.text)
    csvw = csv.DictWriter(csv_out_file, fieldnames = results_of_the_day.keys())
    csvw.writerow(results_of_the_day)
