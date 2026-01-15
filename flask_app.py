print ("FLASK APP VERSION 1")
from flask import Flask, redirect, render_template, request, url_for, abort
from dotenv import load_dotenv
import os
import git
import hmac
import hashlib
from db import db_read, db_write
from auth import login_manager, authenticate, register_user
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
import logging


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Load .env variables
load_dotenv()
W_SECRET = os.getenv("W_SECRET")

# Init flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "supersecret"

# Init auth
login_manager.init_app(app)
login_manager.login_view = "login"

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if getattr(current_user, "role", None) not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def calc_alterskategorie(alter_jahre: int) -> int:
    if 0 <= alter_jahre <= 1:
        return 1
    if 2 <= alter_jahre <= 3:
        return 2
    if 4 <= alter_jahre <= 5:
        return 3
    if 6 <= alter_jahre <= 7:
        return 4
    if 8 <= alter_jahre <= 9:
        return 5
    if 10 <= alter_jahre <= 15:
        return 6
    if 16 <= alter_jahre <= 20:
        return 7
    if 21 <= alter_jahre <= 40:
        return 8
    if 41 <= alter_jahre <= 60:
        return 9
    if 61 <= alter_jahre <= 80:
        return 10
    if 81 <= alter_jahre <= 100:
        return 11
    raise ValueError("Alter ausserhalb 0-100")


def kompatible_empfaenger_blutgruppen(spender_bg: str):
    mapping = {
        "0-":  ["0-", "0+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
        "0+":  ["0+", "A+", "B+", "AB+"],
        "A-":  ["A-", "A+", "AB-", "AB+"],
        "A+":  ["A+", "AB+"],
        "B-":  ["B-", "B+", "AB-", "AB+"],
        "B+":  ["B+", "AB+"],
        "AB-": ["AB-", "AB+"],
        "AB+": ["AB+"],
    }
    return mapping.get(spender_bg, [])



# DON'T CHANGEn 
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

# DON'T CHANGE
@app.post('/update_server')
def webhook():
    x_hub_signature = request.headers.get('X-Hub-Signature')
    if is_valid_signature(x_hub_signature, request.data, W_SECRET):
        repo = git.Repo('./mysite')
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    return 'Unathorized', 401





@app.route("/doctor/dashboard")
@login_required
@role_required("doctor", "admin")
def doctor_dashboard():
    # Eigene Patienten + offene Organ-Warteliste anzeigen
    waiting = db_read("""
        SELECT ko.krankesorganid, ko.organ, ko.dringlichkeit,
               p.patientenid, p.vorname, p.nachname, p.blutgruppe, p.spital,
               a.arztid
        FROM krankesorgan ko
        JOIN patienten p ON p.patientenid = ko.patientenid
        JOIN aerzte a ON a.arztid = p.arztid
        WHERE a.user_id = %s
        ORDER BY ko.dringlichkeit DESC
    """, (current_user.id,))
    return render_template("doctor_dashboard.html", waiting=waiting)




@app.route("/doctor/patient/new", methods=["GET", "POST"])
@login_required
@role_required("doctor", "admin")
def new_patient():
        # Arzt-ID holen (und falls fehlt: automatisch anlegen)
    arzt = db_read("SELECT arztid FROM aerzte WHERE user_id=%s", (current_user.id,))

    if not arzt:
        # Auto-Profil erstellen (für alte Accounts)
        db_write(
            "INSERT INTO aerzte (user_id, vorname, nachname) VALUES (%s, %s, %s)",
            (current_user.id, current_user.username, "Auto")
        )
        arzt = db_read("SELECT arztid FROM aerzte WHERE user_id=%s", (current_user.id,))

    arztid = arzt[0]["arztid"]


    if request.method == "GET":
        return render_template("patient_new.html")

    # Patient speichern
    telefon = request.form["telefonnummer"]
    spital = request.form["spital"]
    vorname = request.form["vorname"]
    nachname = request.form["nachname"]
    gewicht = request.form["gewicht"]
    groesse = request.form["groesse"]
    blutgruppe = request.form["blutgruppe"]
    alter_jahre = int(request.form["alter_jahre"])
    alterskategorie = calc_alterskategorie(alter_jahre)

    db_write("""
        INSERT INTO patienten (arztid, telefonnummer, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie, alter_jahre)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (arztid, telefon, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie, alter_jahre))

    # neueste patientenid holen
    pid = db_read("SELECT patientenid FROM patienten WHERE telefonnummer=%s", (telefon,))[0]["patientenid"]

    # krankes Organ/Warteliste speichern
    organ = request.form["organ"]
    dringlichkeit = request.form["dringlichkeit"]
    db_write("""
        INSERT INTO krankesorgan (patientenid, organ, dringlichkeit)
        VALUES (%s,%s,%s)
    """, (pid, organ, dringlichkeit))

    return redirect(url_for("doctor_dashboard"))


@app.route("/doctor/deceased/new", methods=["GET", "POST"])
@login_required
@role_required("doctor", "admin")
def new_deceased():
    if request.method == "GET":
        return render_template("deceased_new.html")

    tel_angeh = request.form.get("telefonnummerangehorige")
    spital = request.form.get("spital")
    vorname = request.form.get("vorname")
    nachname = request.form.get("nachname")
    gewicht = request.form["gewicht"]
    groesse = request.form["groesse"]
    blutgruppe = request.form["blutgruppe"]
    alter_jahre = int(request.form["alter_jahre"])
    alterskategorie = calc_alterskategorie(alter_jahre)

    db_write("""
        INSERT INTO verstorbener (telefonnummerangehorige, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (tel_angeh, spital, vorname, nachname, gewicht, groesse, blutgruppe, alterskategorie))

    vid = db_read("""
        SELECT verstorbenenid FROM verstorbener
        ORDER BY verstorbenenid DESC LIMIT 1
    """)[0]["verstorbenenid"]

    # Mehrere Organe aus Formular (Checkboxen)
    organs = request.form.getlist("organs")
    for organ in organs:
        db_write("INSERT INTO spenderorgane (verstorbenenid, organ) VALUES (%s,%s)", (vid, organ))

    return redirect(url_for("doctor_dashboard"))


@app.route("/doctor/allocate", methods=["GET", "POST"])
@login_required
@role_required("doctor", "admin")
def allocate():
    suggestions = []
    did_run = False

    if request.method == "POST":
        did_run = True

        spender = db_read("""
            SELECT so.spenderorganid, so.organ,
                v.blutgruppe,
                v.alterskategorie
            FROM spenderorgane so
            JOIN verstorbener v ON v.verstorbenenid = so.verstorbenenid

        """, ())

                for s in spender:
            empfaenger_bgs = kompatible_empfaenger_blutgruppen(s["blutgruppe"])
            if not empfaenger_bgs:
                continue

            placeholders = ",".join(["%s"] * len(empfaenger_bgs))

            match = db_read(f"""
                SELECT ko.krankesorganid, ko.dringlichkeit,
                       p.patientenid, p.vorname, p.nachname, p.spital, p.blutgruppe
                FROM krankesorgan ko
                JOIN patienten p ON p.patientenid = ko.patientenid
                WHERE ko.organ=%s
                  AND p.blutgruppe IN ({placeholders})
                  AND p.alterskategorie=%s
                ORDER BY ko.dringlichkeit DESC
                LIMIT 1
            """, tuple([s["organ"]] + empfaenger_bgs + [s["alterskategorie"]]))

            if match:
                suggestions.append({"spender": s, "match": match[0]})


            

    return render_template("allocate.html", suggestions=suggestions, did_run=did_run)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = authenticate(
            request.form["username"],
            request.form["password"]
        )

        if user:
            login_user(user)

            # Ärzte/Admin direkt ins Arzt-Dashboard
            if getattr(user, "role", None) in ("doctor", "admin"):
                return redirect(url_for("doctor_dashboard"))

            return redirect(url_for("index"))

        error = "Benutzername oder Passwort ist falsch."

    return render_template(
        "auth.html",
        title="In dein Konto einloggen",
        action=url_for("login"),
        button_label="Einloggen",
        error=error,
        footer_text="Noch kein Konto?",
        footer_link_url=url_for("register"),
        footer_link_label="Registrieren"
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        vorname = request.form["vorname"]
        nachname = request.form["nachname"]
        spital = request.form.get("spital") or None
        telefonnummer = request.form.get("telefonnummer") or None


        ok = register_user(username, password, vorname, nachname, spital, telefonnummer)

        if ok:
            return redirect(url_for("login"))

        error = "Benutzername existiert bereits."

    return render_template(
        "auth.html",
        title="Neues Konto erstellen",
        action=url_for("register"),
        button_label="Registrieren",
        error=error,
        footer_text="Du hast bereits ein Konto?",
        footer_link_url=url_for("login"),
        footer_link_label="Einloggen"
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))



# App routes
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if getattr(current_user, "role", None) in ("doctor", "admin"):
        return redirect(url_for("doctor_dashboard"))
    
    # GET
    if request.method == "GET":
        todos = db_read("SELECT id, content, due FROM todos WHERE user_id=%s ORDER BY due", (current_user.id,))
        return render_template("main_page.html", todos=todos)

    # POST
    content = request.form["contents"]
    due = request.form["due_at"]
    db_write("INSERT INTO todos (user_id, content, due) VALUES (%s, %s, %s)", (current_user.id, content, due, ))
    return redirect(url_for("index"))

@app.post("/complete")
@login_required
def complete():
    todo_id = request.form.get("id")
    db_write("DELETE FROM todos WHERE user_id=%s AND id=%s", (current_user.id, todo_id,))
    return redirect(url_for("index"))

@app.route("/users", methods=["GET"])
@login_required
def users():
    users_list = db_read("SELECT username FROM users ORDER BY username", ())
    return render_template("users.html", users=users_list)



@app.route("/dbexplorer", methods=["GET", "POST"])
@login_required
def dbexplorer():
    # Alle Tabellennamen holen
    tables_raw = db_read("SHOW TABLES")
    all_tables = [next(iter(row.values())) for row in tables_raw]  # erste Spalte jedes Dicts

    selected_tables = []
    limit = 50  # Default
    results = {}

    if request.method == "POST":
        # Gewählte Tabellen einsammeln
        selected_tables = request.form.getlist("tables")

        # Limit aus Formular lesen
        limit_str = request.form.get("limit") or ""
        try:
            limit = int(limit_str)
        except ValueError:
            limit = 50

        # Limit ein bisschen absichern
        if limit < 1:
            limit = 1
        elif limit > 1000:
            limit = 1000

        allowed = set(all_tables)

        # Pro gewählter Tabelle Daten abfragen
        for table in selected_tables:
            if table in allowed:  # einfache Absicherung gegen SQL-Injection
                rows = db_read(f"SELECT * FROM `{table}` LIMIT %s", (limit,))
                results[table] = rows

    return render_template(
        "dbexplorer.html",
        all_tables=all_tables,
        selected_tables=selected_tables,
        results=results,
        limit=limit,
    )

# Diese zwei Zeilen MÜSSEN ganz am Ende stehen
if __name__ == "__main__":
    app.run()
