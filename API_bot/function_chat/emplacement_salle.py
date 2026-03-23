from api import app_Router


def emplacement_salle(salle: str):
    app_Router.change_page("plan.html")
    salle = salle.upper()
    if salle.startswith("C0"):
        return f"La salle {salle} se trouve au rez-de-chaussée du bâtiment CERI"
    elif salle.startswith("C1"):
        return f"La salle {salle} se trouve au 2ème étage du bâtiment CERI"

    elif salle.__contains__("ADA") or salle.__contains__("BLAISE"):
        return f"les amphi se trouve au rez-de-chaussée du bâtiment CERI à gauche de l'entrée principale"
