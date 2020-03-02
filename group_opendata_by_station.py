#!/usr/bin/env python
# coding: utf-8

import csv

from collections import Counter

station_list = {}
station_attributes = ['n_amenageur', 'n_operateur', 'n_enseigne', 'id_station', 'n_station', 'ad_station', 'code_insee', 'Xlongitude', 'Ylatitude', 'nbre_pdc' ]
pdc_attributes = ['ad_station', 'id_pdc', 'puiss_max', 'type_prise', 'acces_recharge', 'accessibilité', 'observations', 'date_maj', 'source']

wrong_ortho = {
    "Herault Energies 34" : "Hérault Énergies 34",
    "Montpellier Mediterranee Metropole": "Montpellier Méditerranee Métropole",
    "Toulouse Metropole" : "Toulouse Métropole",
    "SDEY Syndicat Departemental d'Energies de l'Yonne": "SDEY Syndicat Départemental d'Énergies de l'Yonne",
    "TERRITOIRE D'ENERGIE 90": "Territoire d'Énergie 90",
    "SAINT-LOUIS" : "Saint-Louis",
    "PLUS DE BORNES": "Plus de Bornes",
    "ORLEANS METROPOLE" : "Orléans Métropole",
    "S‚olis" : "Séolis",
    "BREST METROPOLE": "Brest Métropole",
    "IONITY": "Ionity",
    "VILLE DE ROSHEIM": "Ville de Rosheim",
    "BOUYGUES ENERGIES ET SERVICES": "Bouygues Énergies et Services",
    "SODETREL" : "Sodetrel",
    "SOREGIES" : "Sorégies",
    "MOBILOIRE": "Mobiloire",
    "MOUVELECVAR": "Mouv Élec Var"
}

def validate_coord(longitude_text):
    try:
        float(longitude_text)
    except ValueError:
        return False
    return True


without_id = []
errors = []

with open('opendata_irve.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=';')
    for row in reader:
        if not row['id_station']:
            without_id.append(row)
            continue
        if not validate_coord(row['Xlongitude']):
            errors.append({"station_id" :  row['id_station'],
                                   "error": "coordonnées non valides",
                                   "detail": row['Xlongitude']
                                  })
            continue
        if not validate_coord(row['Ylatitude']):
            errors.append({"station_id" :  row['id_station'],
                                   "error": "coordonnées non valides",
                                   "detail": row['Ylatitude']
                                  })
            continue
        if not row['id_station'] in station_list:
            station_prop = {key: row[key] for key in station_attributes}
            station_list[row['id_station']] = {'attributes' : station_prop, 'pdc_list': []}
        pdc_prop = {key: row[key] for key in pdc_attributes}
        station_list[row['id_station']]['pdc_list'].append(pdc_prop)

all_prises_types = set()

for station_id, station in station_list.items() :
    if station['attributes']['n_amenageur'] in wrong_ortho.keys():
        station['attributes']['n_amenageur'] = wrong_ortho[station['attributes']['n_amenageur']]
    if station['attributes']['n_enseigne'] in wrong_ortho.keys():
        station['attributes']['n_enseigne'] = wrong_ortho[station['attributes']['n_enseigne']]
    if station['attributes']['n_operateur'] in wrong_ortho.keys():
        station['attributes']['n_operateur'] = wrong_ortho[station['attributes']['n_operateur']]
   
    sources = set([elem['source'] for elem in station['pdc_list']])
    if len(sources) !=1 :
        errors.append({"station_id" : station_id,
                       "error": "plusieurs sources pour un même id",
                       "detail": sources
                      })
    else :
        station['attributes']['source_grouped'] = sources.pop()

    addresses = set([elem['ad_station'] for elem in station['pdc_list']])
    if len(addresses) !=1 :
        errors.append({"station_id" : station_id,
                       "error": "plusieurs adresses pour une même station",
                       "detail": addresses})

    acces_recharge = set([elem['acces_recharge'].strip() for elem in station['pdc_list']])
    if len(acces_recharge) !=1 :
        errors.append({"station_id" : station_id,
                       "error": "plusieurs prix pour une même station",
                       "detail": acces_recharge})
    else :
        station['attributes']['acces_recharge_grouped'] = acces_recharge.pop()

    accessibilite = set([elem['accessibilité'].strip() for elem in station['pdc_list']])
    if len(accessibilite) !=1 :
        errors.append({"station_id" : station_id,
                       "error": "plusieurs horaires pour une même station",
                       "detail": accessibilite})
    else :
        station['attributes']['accessibilité_grouped'] = accessibilite.pop()

    prises = [elem['type_prise'] for elem in station['pdc_list']]
    all_prises_types.update(prises)
    station['attributes']['nb_prises_grouped'] = 0
    station['attributes']['prises_grouped'] = prises


    T2_count = Counter(["t2" in elem.lower() for elem in prises])
    station['attributes']['nb_T2_grouped'] = T2_count[True]
    station['attributes']['nb_prises_grouped'] += T2_count[True]

    T3_count = Counter(["t3" in elem.lower() for elem in prises])
    station['attributes']['nb_T3_grouped'] = T3_count[True]
    station['attributes']['nb_prises_grouped'] += T3_count[True]

    T4_count = Counter(["t4" in elem.lower() for elem in prises])
    if T4_count[True]:
        errors.append({"station_id" : station_id,
                       "error": "type de prise inconnu",
                       "detail": "T4"})

    EF_count = Counter(["EF" in elem for elem in prises])
    EF_other_count = Counter(["E/F" in elem for elem in prises])
    station['attributes']['nb_EF_grouped'] = EF_count[True] + EF_other_count[True]
    station['attributes']['nb_prises_grouped'] += EF_count[True] + EF_other_count[True]

    chademo_count = Counter(["chademo" in elem.lower() for elem in prises])
    station['attributes']['nb_chademo_grouped'] = chademo_count[True]
    station['attributes']['nb_prises_grouped'] += chademo_count[True]

    combo_count = Counter(["combo" in elem.lower() for elem in prises])
    combo_other_count = Counter(["CCS350" in elem for elem in prises])
    station['attributes']['nb_combo_grouped'] = combo_count[True] + combo_other_count[True]
    station['attributes']['nb_prises_grouped'] += combo_count[True] + combo_other_count[True]

    if station['attributes']['nb_prises_grouped'] < len(station['pdc_list']):
        errors.append({"station_id" : station_id,
                       "error": "type de prise inconnu",
                       "detail": prises})

print("{} stations".format(len(station_list)))

print("{} stations sans id (ignorées)".format(len(without_id)))

print("{} stations avec des erreurs :".format(len(errors)))
for error_type, error_count in Counter([elem['error'] for elem in errors]).items():
    print(" > {} : {} stations".format(error_type, error_count))


with open("output/opendata_errors.csv", 'w') as ofile:
    tt = csv.DictWriter(ofile, fieldnames=errors[0].keys())
    tt.writeheader()
    for elem in errors:
        tt.writerow(elem)


with open("output/opendata_stations.csv", 'w') as ofile:
    tt = csv.DictWriter(ofile, fieldnames=station_list['FR*M13*P13029*001']["attributes"].keys())
    tt.writeheader()
    for station_id, station in station_list.items():
        tt.writerow(station['attributes'])
