#!/usr/bin/env python
# coding: utf-8

import csv
import re

from collections import Counter
from enum import IntFlag, auto

class Socket(IntFlag):
    EF = auto()
    T2 = auto()
    CHADEMO = auto()
    CCS = auto()

station_list = {}
station_attributes = [ 'nom_amenageur', 'siren_amenageur', 'contact_amenageur', 'nom_operateur', 'contact_operateur', 'telephone_operateur', 'nom_enseigne', 'id_station_itinerance', 'id_station_local', 'nom_station', 'implantation_station', 'code_insee_commune', 'nbre_pdc', 'station_deux_roues', 'raccordement', 'num_pdl', 'date_mise_en_service', 'observations', 'adresse_station' ]
pdc_attributes = [ 'id_pdc_itinerance', 'id_pdc_local', 'puissance_nominale', 'prise_type_ef', 'prise_type_2', 'prise_type_combo_ccs', 'prise_type_chademo', 'prise_type_autre', 'gratuit', 'paiement_acte', 'paiement_cb', 'paiement_autre', 'tarification', 'condition_acces', 'reservation', 'accessibilite_pmr', 'restriction_gabarit', 'observations', 'date_maj', 'cable_t2_attache', 'datagouv_organization_or_owner', 'horaires' ]
socket_attributes = { 'prise_type_ef': Socket.EF, 'prise_type_2': Socket.T2, 'prise_type_chademo': Socket.CHADEMO, 'prise_type_combo_ccs': Socket.CCS }

errors = []
power_stats = []
wrong_ortho = {}

with open('fixes_networks.csv', 'r') as csv_file:
    csv_reader = csv.DictReader(csv_file, delimiter=',')
    for row in csv_reader:
        wrong_ortho[row["opendata_name"]] = row["better_name"]

def validate_coord(lat_or_lon_text):
    try:
        float(lat_or_lon_text)
    except ValueError:
        return False
    return True

def is_correct_id(station_id):
    if station_id is None:
        return False

    station_id_parts = station_id.split('*')
    station_id = "".join(station_id_parts)
    station_id_parts = station_id.split(' ')
    station_id = "".join(station_id_parts)

    if not station_id.startswith('FR'):
        return False
    if not station_id.startswith('P', 5):
        return False
    return True

def cleanPhoneNumber(phone):
    if re.match("^\+33\d{9}$", phone):
        return phone
    elif re.match("^\+33 \d( \d{2}){4}$", phone):
        return phone.replace(" ", "")
    elif re.match("^33\d{9}$", phone):
        return "+"+phone
    elif re.match("^\d{10}$", phone):
        return "+33" + phone[1:]
    elif re.match("^\d{9}$", phone):
        return "+33" + phone
    elif re.match("^(\d{2}[. -]){4}\d{2}$", phone):
        return "+33" + phone[1:].replace(".", "").replace(" ", "").replace("-", "")
    elif re.match("^\d( \d{3}){3}$", phone):
        return "+33" + phone[1:].replace(" ", "")
    else:
        return None

def compute_max_power_per_socket_type(station, errors):
    """
    Computes the aggregated max power per socket type accross all PDCs (PDLs) associated with the given station.
    Sockets are limited to the max power rating for their type. This is a safe guess needed when a given PDC
    has multiple sockets for a given nominal power rating:
        - E/F: max 4 kw
        - Type 2: max 43 kw
        - Chademo: max 63 kw (in France -> Version 1 only)
        - Combo CCS: currently unlimited
    """
    power_ef = power_t2 = power_chademo = power_ccs = 0
    for pdc in station['pdc_list']:
        socket_mask = sum([ flag for socket_attr, flag in socket_attributes.items() if stringBoolToInt(pdc[socket_attr])==1 ])
        socket_mask = Socket(socket_mask)
        power = float(pdc['puissance_nominale'])
        if power >= 1000:
            errors.append({"station_id" :  station['attributes']['id_station_itinerance'],
                        "source": station['attributes']['source_grouped'],
                        "error": "puissance nominale déclarée suspecte",
                        "detail": "puissance: {}, prises: {}".format(pdc['puissance_nominale'], socket_mask.name)
                        })
            # Convert from W to kW (>2MW should not exist)
            # FIXME: Probably not usefull anymore. Data looks fine.
            if power_ccs >= 2000:
                power_ccs /= 1000
        power_ef = max(power_ef, min(4, power if Socket.EF in socket_mask else 0))
        power_t2 = max(power_t2, min(43, power if Socket.T2 in socket_mask else 0))
        power_chademo = max(power_chademo, min(63, power if Socket.CHADEMO in socket_mask else 0))
        power_ccs = max(power_ccs, power if Socket.CCS in socket_mask else 0)
    return (power_ef, power_t2, power_chademo, power_ccs)

def stringBoolToInt(strbool):
    return 1 if strbool.lower() == 'true' else 0

def transformRef(refIti, refLoc):
    rgx = "FR\*[A-Za-z0-9]{3}\*P[A-Za-z0-9]+\*[A-Za-z0-9]+"
    areRefNoSepEqual = refIti.replace("*", "") == refLoc.replace("*", "")

    if re.match(rgx, refIti):
        return refIti
    elif areRefNoSepEqual and re.match(rgx, refLoc):
        return refLoc
    elif re.match("FR[A-Za-z0-9]{3}P[A-Za-z0-9]+", refIti):
        return "FR*"+refIti[2:5]+"*P"+refIti[6:]
    else:
        return None

errors = []

with open('opendata_irve.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for row in reader:
        if not row['id_station_itinerance']:
            errors.append({"station_id" :  None,
                                   "source": row['datagouv_organization_or_owner'],
                                   "error": "pas d'identifiant ref:EU:EVSE (id_station_itinerance). Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose",
                                   "detail": None
                                  })
            continue
        if row['id_station_itinerance']=="Non concerné":
            # Station non concernée par l'identifiant ref:EU:EVSE (id_station_itinerance). Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose
            continue

        coordsXY = row['coordonneesXY'][1:-1].split(',')
        cleanRef = transformRef(row['id_station_itinerance'], row['id_station_local'])

        if not validate_coord(coordsXY[0]):
            errors.append({"station_id" :  cleanRef,
                                   "source": row['datagouv_organization_or_owner'],
                                   "error": "coordonnées non valides. Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose",
                                   "detail": row['coordonneesXY']
                                  })
            continue
        if not validate_coord(coordsXY[1]):
            errors.append({"station_id" :  cleanRef,
                                   "source": row['datagouv_organization_or_owner'],
                                   "error": "coordonnées non valides. Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose",
                                   "detail": row['coordonneesXY']
                                  })
            continue

        if not is_correct_id(cleanRef):
            errors.append({"station_id" : cleanRef,
                   "source": row['datagouv_organization_or_owner'],
                   "error": "le format de l'identifiant ref:EU:EVSE (id_station_itinerance) n'est pas valide. Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose",
                   "detail": "iti: %s, local: %s" % (row['id_station_itinerance'], row['id_station_local'])})
            continue

        if not cleanRef in station_list:
            station_prop = {key: row[key] if row[key] != "null" else "" for key in station_attributes}
            station_prop['Xlongitude'] = float(coordsXY[0])
            station_prop['Ylatitude'] = float(coordsXY[1])
            phone = cleanPhoneNumber(row['telephone_operateur'])
            station_list[cleanRef] = {'attributes' : station_prop, 'pdc_list': []}

            # Non-blocking issues
            if phone is None and row['telephone_operateur']!= "":
                station_prop['telephone_operateur'] = None
                errors.append({"station_id" : cleanRef,
                   "source": row['datagouv_organization_or_owner'],
                   "error": "le numéro de téléphone de l'opérateur (telephone_operateur) est dans un format invalide",
                   "detail": row['telephone_operateur']})
            elif phone is not None:
                station_prop['telephone_operateur'] = phone
            else:
                station_prop['telephone_operateur'] = None

            if row['station_deux_roues'].lower() not in ['true', 'false', '']:
                station_prop['station_deux_roues'] = None
                errors.append({"station_id" : cleanRef,
                   "source": row['datagouv_organization_or_owner'],
                   "error": "le champ station_deux_roues n'est pas valide",
                   "detail": row['station_deux_roues']})
            else:
                station_prop['station_deux_roues'] = row['station_deux_roues'].lower()

        pdc_prop = {key: row[key] for key in pdc_attributes}
        station_list[cleanRef]['pdc_list'].append(pdc_prop)

# ~ all_prises_types = set()

for station_id, station in station_list.items() :
    if station['attributes']['nom_amenageur'] in wrong_ortho.keys():
        station['attributes']['nom_amenageur'] = wrong_ortho[station['attributes']['nom_amenageur']]
    if station['attributes']['nom_enseigne'] in wrong_ortho.keys():
        station['attributes']['nom_enseigne'] = wrong_ortho[station['attributes']['nom_enseigne']]
    if station['attributes']['nom_operateur'] in wrong_ortho.keys():
        station['attributes']['nom_operateur'] = wrong_ortho[station['attributes']['nom_operateur']]

    station['attributes']['id_station_itinerance'] = station_id
    sources = set([elem['datagouv_organization_or_owner'] for elem in station['pdc_list']])
    if len(sources) !=1 :
        errors.append({"station_id" : station_id,
                       "source": "multiples",
                       "error": "plusieurs sources pour un même id",
                       "detail": sources
                      })
    station['attributes']['source_grouped'] = list(sources)[0]

    horaires = set([elem['horaires'].strip() for elem in station['pdc_list']])
    if len(horaires) !=1 :
        station['attributes']['horaires_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs horaires pour une même station",
                       "detail": horaires})
    else :
        station['attributes']['horaires_grouped'] = list(horaires)[0]

    gratuit = set([elem['gratuit'].strip() for elem in station['pdc_list']])
    if len(gratuit) !=1 :
        station['attributes']['gratuit_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de gratuité (gratuit) pour une même station",
                       "detail": gratuit})
    else :
        station['attributes']['gratuit_grouped'] = list(gratuit)[0]

    paiement_acte = set([elem['paiement_acte'].strip() for elem in station['pdc_list']])
    if len(paiement_acte) !=1 :
        station['attributes']['paiement_acte_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de paiement (paiement_acte) pour une même station",
                       "detail": paiement_acte})
    else :
        station['attributes']['paiement_acte_grouped'] = list(paiement_acte)[0]

    paiement_cb = set([elem['paiement_cb'].strip() for elem in station['pdc_list']])
    if len(paiement_cb) !=1 :
        station['attributes']['paiement_cb_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de paiement (paiement_cb) pour une même station",
                       "detail": paiement_cb})
    else :
        station['attributes']['paiement_cb_grouped'] = list(paiement_cb)[0]

    reservation = set([elem['reservation'].strip() for elem in station['pdc_list']])
    if len(reservation) !=1 :
        station['attributes']['reservation_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de réservation pour une même station",
                       "detail": reservation})
    else :
        station['attributes']['reservation_grouped'] = list(reservation)[0]

    accessibilite_pmr = set([elem['accessibilite_pmr'].strip() for elem in station['pdc_list']])
    if len(accessibilite_pmr) !=1 :
        station['attributes']['accessibilite_pmr_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos d'accessibilité PMR (accessibilite_pmr) pour une même station",
                       "detail": accessibilite_pmr})
    else :
        station['attributes']['accessibilite_pmr_grouped'] = list(accessibilite_pmr)[0]

    if len(station['pdc_list']) != int(station['attributes']['nbre_pdc']):
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "le nombre de point de charge de la station n'est pas cohérent avec la liste des points de charge fournie",
                       "detail": "{} points de charge indiqués pour la station (nbre_pdc) mais {} points de charge listés".format(station['attributes']['nbre_pdc'], len(station['pdc_list']))})        
        station['attributes']['nbre_pdc'] = None

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

    power_grouped_values = compute_max_power_per_socket_type(station, errors)
    power_stats.append(power_grouped_values)
    power_props = ['power_ef_grouped', 'power_t2_grouped', 'power_chademo_grouped', 'power_ccs_grouped']
    station['attributes'].update(zip(power_props, power_grouped_values))

print("Computed power stats:")
print("       EF  |   T2  | Chademo |  CCS  |")
for power_set, count in Counter(power_stats).most_common():
    print(" >    {:4.2f}   {:5.2f}    {:5.2f}   {:6.2f} : {} occurences".format(*power_set, count))

print("{} stations".format(len(station_list)))

print("{} points de charge avec des erreurs :".format(len(errors)))
for error_type, error_count in Counter([elem['error'] for elem in errors]).items():
    print(" > {} : {} éléments".format(error_type, error_count))

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
