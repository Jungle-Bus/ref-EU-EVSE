# ref:EU:EVSE

Retraitement des données open data des points de recharge pour véhicules électriques pour intégration dans OpenStreetMap.

Le fichier open data utilisé est le fichier consolidé des bornes de rechage pour véhicules électriques, publié sur [datagouv](https://www.data.gouv.fr/fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques). Il s'agit d'un jeu de données qui regroupe l'ensemble des données produites par les différents acteurs territoriaux.

## Installation

### Créer le dossier de sortie

Les scripts génèrent des fichiers dans le dossier `output/`. Créez ce dossier avant d'exécuter les scripts :

```bash
mkdir -p output
```

### Récupérer le jeu de données IRVE depuis data.gouv.fr

Le fichier `opendata_irve.csv` doit être téléchargé depuis data.gouv.fr. 

https://www.data.gouv.fr/fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques

**URL de téléchargement direct actuelle** (peut changer) :
```
https://www.data.gouv.fr/fr/datasets/r/2729b192-40ab-4454-904d-735084dca3a3
```

Pour télécharger le fichier avec curl:

```bash
curl -L https://www.data.gouv.fr/fr/datasets/r/2729b192-40ab-4454-904d-735084dca3a3 -o opendata_irve.csv
```

**Note** : L'ID dans l'URL peut changer si le jeu de données est mis à jour. Vérifiez régulièrement la page du jeu de données pour obtenir l'URL la plus récente.

Contrairement à ce que son nom laisse entendre, le jeu de données open data ne contient pas d'informations sur les bornes : il contient des points de recharge, ainsi que des informations sur les stations.

![définition des termes borne/station/point de charge](https://afirev.fr/wp-content/uploads/2019/08/Archi-station-borne-point-Fr-1024x610.jpg)
*illustration issue de la [doc de l'AFIREV](https://afirev.fr/fr/definition-des-termes-de-la-mobilite-electrique/)*

Ce sont les bornes qui nous intéressent pour OpenStreetMap. À défaut, la consolidation suivante regroupe les informations open data par station (en recalculant notamment les informations des types de prise par station à partir des points de recharge).

En complément du regroupement par station, le retraitement suivant effectue divers modifications ou vérifications :

* vérification sommaire de la validité des coordonnées géographiques
* vérification sommaire de la validité de l'identifiant d'itinérance (`id_station_itinerance`) qui est ajouté dans OSM dans la clef `ref:EU:EVSE`
* vérification sommaire de la validité du numéro de téléphone
* correction de plusieurs attributs tels que les noms de l'opérateur, de l'aménageur et du réseau à partir d'une liste de référence (modifiable [ici](https://github.com/Jungle-Bus/ref-EU-EVSE/blob/master/fixes_networks.csv))
* vérification des doublons (une même station listée plusieurs fois)
* vérifications diverses de cohérence entre les informations des points de recharge et de la station
* etc

Ces opérations de regroupement et vérifications peuvent révéler des incohérences dans les données. Dans ce cas le champ de sortie est laissé vide. Des champs supplémentaires peuvent être ajouté dans certains cas :
* `nbre_pdc_unsure` : ce champ est ajouté lors du regroupement lorsque le `nbr_pdc` déclaré pour une station ne correspond pas aux nombres de PDCs effectivement trouvés (exemple `nbr_pdc = 2` et 4 PDCs avec le même station_id -> dans ce cas, la sortie contiendra `nbr_pdc = None` et `nbr_pdc_unsure = 2`)

Voici les fichiers de sortie du retraitement :

* la liste des stations https://raw.githubusercontent.com/Jungle-Bus/ref-EU-EVSE/gh-pages/opendata_stations.csv
* la liste des couples opérateur / réseau (à des fins de corrections de typo, ajout de tag wikidata, etc) : https://github.com/Jungle-Bus/ref-EU-EVSE/raw/gh-pages/opendata_networks.csv
* la liste des erreurs rencontrées durant le traitement (coordonnées invalides, nombre de points de charge d'une station non cohérente, doublons, etc) : https://raw.githubusercontent.com/Jungle-Bus/ref-EU-EVSE/gh-pages/opendata_errors.csv

Les données open data semblent être mises à jour tous les jours. Le présent traitement est effectué une fois par mois (voir [l'historique des traitements](https://github.com/Jungle-Bus/ref-EU-EVSE/actions?query=branch%3Agh-pages))

Les données consolidées ici sont utilisées par [l'analyse Osmose 8410](https://osmose.openstreetmap.fr/en/issues/open?item=8410).

La correspondance entre les attributs est documentée sur le [wiki](https://wiki.openstreetmap.org/wiki/France/data.gouv.fr/Bornes_de_Recharge_pour_V%C3%A9hicules_%C3%89lectriques) et accessible dans le [code source d'Osmose](https://github.com/osm-fr/osmose-backend/blob/master/analysers/analyser_merge_charging_station_FR.py).
