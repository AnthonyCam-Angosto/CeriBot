def declaration():
    return [visualiser_planning_formation,recherche_salle_disponnible,]

visualiser_planning_formation = {
    "name": "visualiser_planning_formation",
    "description": "Visualise le planning d'une journée d'une formation universitaire",
    "parameters": {
    "type": "object",
    "properties": {
     "date": {
        "type": "string",
        "format": "date",
        "description": "La date spécifique pour laquelle visualiser le planning (au format DD-MM)."
      },
      "filiere": {
        "type": "string",
        "enum": ["informatique","ilsen","ia","syrius"],
        "description": "Le nom de la filière pour laquelle visualiser le planning."
      },
      "type_formation": {
        "type": "string",
        "enum": ["licence", "master"],
        "description": "Le type de formation à visualiser (licence, master)."
      },
      "niveau_etudes": {
        "type": "integer",
        "minimum": 1,
        "maximum": 3,
        "description": "Le niveau d'études (pour les licences et masters, ex: 1 pour L1, 3 pour L3)."
      },
      "mode_etudes":{
          "type":"string",
          "enum":["classic","alternance"],
          "description":"le mode d'etude qui soit classic ou alternance"
      }
    },
  }
}

recherche_salle_disponnible = {
    "name": "recherche_salle_disponnible",
    "description": "recherche de salle disponnible dans le batiment CERI",
    "parameters": {
        "type": "object",
        "properties": {
            "date": {
            "type": "string",
            "format": "date",
            "description": "La date spécifique pour laquelle recherche une salle (au format DD-MM)."
            },
            "heure de debut": {
                "type": "string",
                "description": "L'heure de début de voulu"
            },
            "temps d'utilisation de la salle":{
                "type":"string",
                "enum":["1h30","3h","4h30","6h"],
                "description": "durée d'utilisation voulue"
            }   
        }
    }
}