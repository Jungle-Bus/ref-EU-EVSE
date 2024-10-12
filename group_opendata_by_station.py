#!/usr/bin/env python
# coding: utf-8

import csv
import re

from collections import Counter

station_list = {}
station_attributes = [ 'nom_amenageur', 'siren_amenageur', 'contact_amenageur', 'nom_operateur', 'contact_operateur', 'telephone_operateur', 'nom_enseigne', 'id_station_itinerance', 'id_station_local', 'nom_station', 'implantation_station', 'code_insee_commune', 'nbre_pdc', 'station_deux_roues', 'raccordement', 'num_pdl', 'date_mise_en_service', 'observations', 'adresse_station' ]
pdc_attributes = [ 'id_pdc_itinerance', 'id_pdc_local', 'puissance_nominale', 'prise_type_ef', 'prise_type_2', 'prise_type_combo_ccs', 'prise_type_chademo', 'prise_type_autre', 'gratuit', 'paiement_acte', 'paiement_cb', 'paiement_autre', 'tarification', 'condition_acces', 'reservation', 'accessibilite_pmr', 'restriction_gabarit', 'observations', 'date_maj', 'cable_t2_attache', 'datagouv_organization_or_owner', 'horaires' ]

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

    if not station_id.startswith('P', 5):
        return False
    return True

def cleanPhoneNumber(phone):
    if re.match(r"^\+33\d{9}$", phone):
        return phone
    elif re.match(r"^\+33 \d( \d{2}){4}$", phone):
        return phone.replace(" ", "")
    elif re.match(r"^33\d{9}$", phone):
        return "+"+phone
    elif re.match(r"^\d{10}$", phone):
        return "+33" + phone[1:]
    elif re.match(r"^\d{9}$", phone):
        return "+33" + phone
    elif re.match(r"^(\d{2}[. -]){4}\d{2}$", phone):
        return "+33" + phone[1:].replace(".", "").replace(" ", "").replace("-", "")
    elif re.match(r"^\d( \d{3}){3}$", phone):
        return "+33" + phone[1:].replace(" ", "")
    else:
        return None

def stringBoolToInt(strbool):
    return 1 if strbool.lower() == 'true' else 0

def transformRef(refIti, refLoc):
    rgx = r"^[A-Z]{2}\*[A-Za-z0-9]{3}\*P[A-Za-z0-9]+\*[A-Za-z0-9]+"
    areRefNoSepEqual = refIti.replace("*", "") == refLoc.replace("*", "")

    if re.match(rgx, refIti):
        return refIti
    elif areRefNoSepEqual and re.match(rgx, refLoc):
        return refLoc
    elif re.match("^[A-Z]{2}[A-Za-z0-9]{3}P[A-Za-z0-9]+", refIti):
        return refIti[:2]+"*"+refIti[2:5]+"*P"+refIti[6:]
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

        cleanRef = transformRef(row['id_station_itinerance'], row['id_station_local'])

        # Overkill given that this data should have passed through this code:
        # https://github.com/datagouv/datagouvfr_data_pipelines/blob/75db0b1db3fd79407a1526b0950133114fefaa0f/schema/utils/geo.py#L33
        if not validate_coord(row["consolidated_longitude"]) or not validate_coord(row["consolidated_latitude"]):
            errors.append({"station_id" :  cleanRef or row['id_station_itinerance'],
                "source": row['datagouv_organization_or_owner'],
                "error": "coordonnées non valides. Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose",
                "detail": "consolidated_longitude: {}, consolidated_latitude: {}".format(row['consolidated_longitude'], row["consolidated_latitude"])
                })
            continue

        if not is_correct_id(cleanRef):
            errors.append({"station_id" : cleanRef or row['id_station_itinerance'],
                   "source": row['datagouv_organization_or_owner'],
                   "error": "le format de l'identifiant ref:EU:EVSE (id_station_itinerance) n'est pas valide. Ce point de charge est ignoré et sa station ne sera pas présente dans l'analyse Osmose",
                   "detail": "iti: %s, local: %s" % (row['id_station_itinerance'], row['id_station_local'])})
            continue

        if not cleanRef in station_list:
            station_prop = {}
            for key in station_attributes :
                station_prop[key] = row[key]
                if row[key] == "null":
                    station_prop[key] = ""
                elif row[key] in wrong_ortho.keys():
                    station_prop[key] = wrong_ortho[row[key]]

            station_prop['Xlongitude'] = float(row['consolidated_longitude'])
            station_prop['Ylatitude'] = float(row['consolidated_latitude'])
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

    gratuit = set([elem['gratuit'].strip().lower() for elem in station['pdc_list']])
    if len(gratuit) !=1 :
        station['attributes']['gratuit_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de gratuité (gratuit) pour une même station",
                       "detail": gratuit})
    else :
        station['attributes']['gratuit_grouped'] = list(gratuit)[0]

    paiement_acte = set([elem['paiement_acte'].strip().lower() for elem in station['pdc_list']])
    if len(paiement_acte) !=1 :
        station['attributes']['paiement_acte_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de paiement (paiement_acte) pour une même station",
                       "detail": paiement_acte})
    else :
        station['attributes']['paiement_acte_grouped'] = list(paiement_acte)[0]

    paiement_cb = set([elem['paiement_cb'].strip().lower() for elem in station['pdc_list']])
    if len(paiement_cb) !=1 :
        station['attributes']['paiement_cb_grouped'] = None
        errors.append({"station_id" : station_id,
                       "source": station['attributes']['source_grouped'],
                       "error": "plusieurs infos de paiement (paiement_cb) pour une même station",
                       "detail": paiement_cb})
    else :
        station['attributes']['paiement_cb_grouped'] = list(paiement_cb)[0]

    reservation = set([elem['reservation'].strip().lower() for elem in station['pdc_list']])
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
