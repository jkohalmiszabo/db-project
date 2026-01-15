import random
from db import db_write, db_read
from flask_app import calc_alterskategorie

ORGANE = ["Herz", "Leber", "Niere", "Lunge", "Bauchspeicheldrüse", "Darm"]
BLUTGRUPPEN = ["0-", "0+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
SPITAELER = ["Inselspital", "Kantonsspital", "Unispital", "Stadtspital"]

def get_any_arztid():
    arzt = db_read("SELECT arztid FROM aerzte LIMIT 1", ())
    if not arzt:
        raise Exception("Kein Arzt vorhanden! Bitte zuerst einen Account registrieren.")
    return arzt[0]["arztid"]

def create_patients(n=400):
    arztid = get_any_arztid()

    print(f"Erstelle {n} Patienten...")

    for i in range(n):
        vorname = f"Patient{i}"
        nachname = f"Test{i}"
        telefon = f"079{i:07d}"
        spital = random.choice(SPITAELER)
        gewicht = round(random.uniform(50, 110), 1)
        groesse = round(random.uniform(150, 200), 1)
        blutgruppe = random.choice(BLUTGRUPPEN)
        alter = random.randint(1, 90)
        alterskategorie = calc_alterskategorie(alter)

        db_write("""
            INSERT INTO patienten 
            (arztid, telefonnummer, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie, alter_jahre)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (arztid, telefon, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie, alter))

        pid = db_read("SELECT patientenid FROM patienten WHERE telefonnummer=%s", (telefon,))[0]["patientenid"]

        organ = random.choice(ORGANE)
        dringlichkeit = random.randint(1, 10)

        db_write("""
            INSERT INTO krankesorgan (patientenid, organ, dringlichkeit)
            VALUES (%s,%s,%s)
        """, (pid, organ, dringlichkeit))

    print("400 Patienten erstellt.")


def create_one_deceased():
    print("Erstelle 1 Verstorbenen mit allen Organen...")

    vorname = "Spender"
    nachname = "Test"
    tel = "0800000000"
    spital = random.choice(SPITAELER)
    gewicht = round(random.uniform(60, 100), 1)
    groesse = round(random.uniform(160, 190), 1)
    blutgruppe = random.choice(BLUTGRUPPEN)
    alter = random.randint(18, 70)
    alterskategorie = calc_alterskategorie(alter)

    db_write("""
        INSERT INTO verstorbener 
        (telefonnummerangehorige, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (tel, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie))

    vid = db_read("SELECT verstorbenenid FROM verstorbener ORDER BY verstorbenenid DESC LIMIT 1")[0]["verstorbenenid"]

    for organ in ORGANE:
        db_write("INSERT INTO spenderorgane (verstorbenenid, organ) VALUES (%s,%s)", (vid, organ))

    print("Verstorbener mit 6 Organen erstellt.")


if __name__ == "__main__":
    create_patients(400)
    create_one_deceased()
    print("Testdaten erfolgreich erstellt.")
