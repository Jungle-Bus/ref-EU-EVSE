#!/usr/bin/env python
# coding: utf-8

import csv

from collections import Counter

station_list = {}
station_attributes = [ 'nom_amenageur', 'siren_amenageur', 'contact_amenageur', 'nom_operateur', 'contact_operateur', 'telephone_operateur', 'nom_enseigne', 'id_station_itinerance', 'id_station_local', 'nom_station', 'implantation_station', 'code_insee_commune', 'nbre_pdc', 'station_deux_roues', 'raccordement', 'num_pdl', 'date_mise_en_service', 'observations' ]
pdc_attributes = [ 'id_pdc_itinerance', 'id_pdc_local', 'puissance_nominale', 'prise_type_ef', 'prise_type_2', 'prise_type_combo_ccs', 'prise_type_chademo', 'prise_type_autre', 'gratuit', 'paiement_acte', 'paiement_cb', 'paiement_autre', 'tarification', 'condition_acces', 'reservation', 'accessibilite_pmr', 'restriction_gabarit', 'observations', 'date_maj', 'cable_t2_attache', 'datagouv_organization_or_owner', 'adresse_station', 'horaires' ]

wrong_ortho = {
    "Herault Energies 34" : "Hérault Énergies 34",
    "Montpellier Mediterranee Metropole": "Montpellier Méditerranée Métropole",
    "Toulouse Metropole" : "Toulouse Métropole",
    "SDEY Syndicat Departemental d'Energies de l'Yonne": "SDEY Syndicat Départemental d'Énergies de l'Yonne",
    "TERRITOIRE D'ENERGIE 90": "Territoire d'Énergie 90",
    "TE90": "Territoire d'Énergie 90",
    "SAINT-LOUIS" : "Saint-Louis",
    "PLUS DE BORNES": "Plus de Bornes",
    "ORLEANS METROPOLE" : "Orléans Métropole",
    "S‚olis" : "Séolis",
    "BREST METROPOLE": "Brest Métropole",
    "IONITY": "Ionity",
    "IZIVIA": "Izivia",
    "SIMONE": "Simone",
    "CANTAL": "Cantal",
    "ISTRES": "Istres",
    "SYDEV": "SyDEV",
    "La borne �lectrique": "La Borne Électrique",
    "Morbihan énergies": "Morbihan Énergies",
    "Pass pass electrique": "Pass pass électrique",
    "VILLE DE ROSHEIM": "Ville de Rosheim",
    "CC VITRY CHAMPAGNE ET DER": "Communauté de communes Vitry, Champagne et Der",
    "BOUYGUES ENERGIES ET SERVICES": "Bouygues Énergies et Services",
    "CITEOS-FRESHMILE" : "Freshmile",
    "SODETREL" : "Sodetrel",
    "SOREGIES" : "Sorégies",
    "MOBILOIRE": "Mobiloire",
    "MOUVELECVAR": "Mouv Élec Var"
}

def validate_coord(lat_or_lon_text):
    try:
        float(lat_or_lon_text)
    except ValueError:
        return False
    return True

def is_correct_id(station_id):
    station_id_parts = station_id.split('*')
    station_id = "".join(station_id_parts)
    station_id_parts = station_id.split(' ')
    station_id = "".join(station_id_parts)

    if not station_id.startswith('FR'):
        return False
    if not station_id.startswith('P', 5):
        return False
    return True

def stringBoolToInt(strbool):
    return 1 if strbool.lower() == 'true' else 0

errors = []

with open('opendata_irve.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for row in reader:
        if not row['id_station_itinerance']:
            errors.append({"station_id" :  None,
                                   "source": row['datagouv_organization_or_owner'],
                                   "error": "pas d'identifiant ref:EU:EVSE (id_station_itinerance). Cette station est ignorée et ne sera pas présente dans l'analyse Osmose",
                                   "detail": None
                                  })
            continue
        coordsXY = row['coordonneesXY'][1:-1].split(',')
        if not validate_coord(coordsXY[0]):
            errors.append({"station_id" :  row['id_station_itinerance'],
                                   "source": row['datagouv_organization_or_owner'],
                                   "error": "coordonnées non valides. Cette station est ignorée et ne sera pas présente dans l'analyse Osmose",
                                   "detail": row['coordonneesXY']
                                  })
            continue
        if not validate_coord(coordsXY[1]):
            errors.append({"station_id" :  row['id_station_itinerance'],
                                   "source": row['datagouv_organization_or_owner'],
                                   "error": "coordonnées non valides. Cette station est ignorée et ne sera pas présente dans l'analyse Osmose",
                                   "detail": row['coordonneesXY']
                                  })
            continue

        if not is_correct_id(row['id_station_itinerance']):
            errors.append({"station_id" : row['id_station_itinerance'],
                   "source": row['datagouv_organization_or_owner'],
                   "error": "le format de l'identifiant ref:EU:EVSE (id_station_itinerance) n'est pas valide",
                   "detail": row['id_station_itinerance']})
            continue

        if not row['id_station_itinerance'] in station_list:
            station_prop = {key: row[key] for key in station_attributes}
            station_prop['Xlongitude'] = float(coordsXY[0])
            station_prop['Ylatitude'] = float(coordsXY[1])
            station_list[row['id_station_itinerance']] = {'attributes' : station_prop, 'pdc_list': []}
        pdc_prop = {key: row[key] for key in pdc_attributes}
        station_list[row['id_station_itinerance']]['pdc_list'].append(pdc_prop)

# ~ all_prises_types = set()

for station_id, station in station_list.items() :
    if station['attributes']['nom_amenageur'] in wrong_ortho.keys():
        station['attributes']['nom_amenageur'] = wrong_ortho[station['attributes']['nom_amenageur']]
    if station['attributes']['nom_enseigne'] in wrong_ortho.keys():
        station['attributes']['nom_enseigne'] = wrong_ortho[station['attributes']['nom_enseigne']]
    if station['attributes']['nom_operateur'] in wrong_ortho.keys():
        station['attributes']['nom_operateur'] = wrong_ortho[station['attributes']['nom_operateur']]

    sources = set([elem['datagouv_organization_or_owner'] for elem in station['pdc_list']])
    if len(sources) !=1 :
        errors.append({"station_id" : station_id,
                       "source": "multiples",
                       "error": "plusieurs sources pour un même id",
                       "detail": sources
                      })
    station['attributes']['source_grouped'] = sources.pop()

    addresses = set([elem['adresse_station'] for elem in station['pdc_list']])
    if len(addresses) !=1 :
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs adresses pour une même station",
                       "detail": addresses})

    condition_acces = set([elem['condition_acces'].strip() for elem in station['pdc_list']])
    if len(condition_acces) !=1 :
        station['attributes']['condition_acces_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs conditions d'accès pour une même station",
                       "detail": condition_acces})
    else :
        station['attributes']['condition_acces_grouped'] = condition_acces.pop()

    horaires = set([elem['horaires'].strip() for elem in station['pdc_list']])
    if len(horaires) !=1 :
        station['attributes']['horaires_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs horaires pour une même station",
                       "detail": horaires})
    else :
        station['attributes']['horaires_grouped'] = horaires.pop()


    station['attributes']['nb_prises_grouped'] = len(station['pdc_list'])

    EF_count = sum([ stringBoolToInt(elem['prise_type_ef']) for elem in station['pdc_list'] ])
    station['attributes']['nb_EF_grouped'] = EF_count

    T2_count = sum([ stringBoolToInt(elem['prise_type_2']) for elem in station['pdc_list'] ])
    station['attributes']['nb_T2_grouped'] = T2_count

    combo_count = sum([ stringBoolToInt(elem['prise_type_combo_ccs']) for elem in station['pdc_list'] ])
    station['attributes']['nb_combo_ccs_grouped'] = combo_count

    chademo_count = sum([ stringBoolToInt(elem['prise_type_chademo']) for elem in station['pdc_list'] ])
    station['attributes']['nb_chademo_grouped'] = chademo_count

    autre_count = sum([ stringBoolToInt(elem['prise_type_autre']) for elem in station['pdc_list'] ])
    station['attributes']['nb_autre_grouped'] = autre_count

    if (EF_count + T2_count + combo_count + chademo_count + autre_count) == 0:
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "aucun type de prise précisé sur l'ensemble des points de charge",
                       "detail": "nb pdc: %s" % (len(station['pdc_list']))
                       })

print("{} stations".format(len(station_list)))

print("{} stations avec des erreurs :".format(len(errors)))
for error_type, error_count in Counter([elem['error'] for elem in errors]).items():
    print(" > {} : {} stations".format(error_type, error_count))


with open("output/opendata_errors.csv", 'w') as ofile:
    tt = csv.DictWriter(ofile, fieldnames=errors[0].keys())
    tt.writeheader()
    for elem in errors:
        tt.writerow(elem)

with open("output/opendata_stations.csv", 'w') as ofile:
    tt = csv.DictWriter(ofile, fieldnames=station_list[list(station_list)[0]]["attributes"].keys())
    tt.writeheader()
    for station_id, station in station_list.items():
        tt.writerow(station['attributes'])
