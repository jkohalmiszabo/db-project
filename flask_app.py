print("FLASK APP VERSION 1")

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


# DON'T CHANGE
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split("=", 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, "latin-1")
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)


# DON'T CHANGE
@app.post("/update_server")
def webhook():
    x_hub_signature = request.headers.get("X-Hub-Signature")
    if is_valid_signature(x_hub_signature, request.data, W_SECRET):
        repo = git.Repo("./mysite")
        origin = repo.remotes.origin
        origin.pull()
        return "Updated PythonAnywhere successfully", 200
    return "Unathorized", 401


# ======= NEU: Startseite nach Login (2 Buttons) =======
@app.route("/doctor/home")
@login_required
@role_required("doctor", "admin")
def doctor_home():
    return render_template("doctor_home.html")


@app.route("/doctor/warteliste")
@login_required
@role_required("doctor", "admin")
def offizielle_warteliste():
    rows = db_read("""
        SELECT 
          p.vorname,
          p.nachname,
          p.alterskategorie,
          ko.organ,
          p.blutgruppe,
          ko.dringlichkeit,
          LEAST(10, ko.dringlichkeit + FLOOR(TIMESTAMPDIFF(DAY, ko.created_at, NOW())/30)) AS effektive_dringlichkeit,
          ko.created_at AS eingabedatum,
          p.arztid,
          a.user_id AS owner_user_id
        FROM krankesorgan ko
        JOIN patienten p ON p.patientenid = ko.patientenid
        JOIN aerzte a ON a.arztid = p.arztid
        LEFT JOIN zuteilung z ON z.krankesorganid = ko.krankesorganid
                             AND z.status IN ('proposed','confirmed')
        WHERE z.zuteilungid IS NULL
        ORDER BY effektive_dringlichkeit DESC, ko.created_at ASC
    """)
    return render_template("warteliste.html", waiting=rows)


# ======= FIX: Dashboard Route war weg! =======
@app.route("/doctor/dashboard")
@login_required
@role_required("doctor", "admin")
def doctor_dashboard():
    waiting = db_read("""
        SELECT 
          p.patientenid,
          p.vorname,
          p.nachname,
          p.arztid,
          p.spital,
          p.telefonnummer,
          p.gewicht,
          p.groesse,
          p.alter_jahre,
          p.alterskategorie,
          p.blutgruppe,
          ko.krankesorganid,
          ko.organ,
          ko.dringlichkeit,
          LEAST(10, ko.dringlichkeit + FLOOR(TIMESTAMPDIFF(DAY, ko.created_at, NOW())/30)) AS effektive_dringlichkeit,
          ko.created_at AS eingabedatum
        FROM krankesorgan ko
        JOIN patienten p ON p.patientenid = ko.patientenid
        JOIN aerzte a ON a.arztid = p.arztid
        LEFT JOIN zuteilung z ON z.krankesorganid = ko.krankesorganid
                             AND z.status IN ('proposed','confirmed')
        WHERE a.user_id = %s
          AND z.zuteilungid IS NULL
        ORDER BY effektive_dringlichkeit DESC, ko.created_at ASC
    """, (current_user.id,))
    return render_template("doctor_dashboard.html", waiting=waiting)



@app.route("/doctor/warteliste/edit/<int:krankesorganid>", methods=["GET", "POST"])
@login_required
@role_required("doctor", "admin")
def edit_waitlist_entry(krankesorganid):
    # Datensatz holen + Besitzer prüfen (nur eigener Eintrag, ausser admin)
    row = db_read("""
        SELECT
          ko.krankesorganid, ko.organ, ko.dringlichkeit, ko.created_at,
          p.patientenid, p.vorname, p.nachname, p.spital, p.telefonnummer,
          p.gewicht, p.groesse, p.blutgruppe, p.alter_jahre, p.alterskategorie,
          a.user_id AS owner_user_id
        FROM krankesorgan ko
        JOIN patienten p ON p.patientenid = ko.patientenid
        JOIN aerzte a ON a.arztid = p.arztid
        WHERE ko.krankesorganid = %s
        LIMIT 1
    """, (krankesorganid,), single=True)

    if not row:
        abort(404)

    # doctor darf nur eigene Einträge editieren, admin alles
    if current_user.role != "admin" and row["owner_user_id"] != current_user.id:
        abort(403)

    if request.method == "GET":
        return render_template("patient_edit.html", row=row)

    # POST: Werte speichern
    db_write("""
        UPDATE patienten
        SET vorname=%s, nachname=%s, spital=%s, telefonnummer=%s,
            gewicht=%s, groesse=%s, blutgruppe=%s, alter_jahre=%s, alterskategorie=%s
        WHERE patientenid=%s
    """, (
        request.form["vorname"],
        request.form["nachname"],
        request.form["spital"],
        request.form["telefonnummer"],
        request.form["gewicht"],
        request.form["groesse"],
        request.form["blutgruppe"],
        int(request.form["alter_jahre"]),
        calc_alterskategorie(int(request.form["alter_jahre"])),
        row["patientenid"]
    ))

    db_write("""
        UPDATE krankesorgan
        SET organ=%s, dringlichkeit=%s
        WHERE krankesorganid=%s
    """, (
        request.form["organ"],
        int(request.form["dringlichkeit"]),
        krankesorganid
    ))

    # zurück zur Warteliste
    return redirect(url_for("doctor_dashboard"))



@app.route("/doctor/patient/new", methods=["GET", "POST"])
@login_required
@role_required("doctor", "admin")
def new_patient():
    arzt = db_read("SELECT arztid FROM aerzte WHERE user_id=%s", (current_user.id,))

    if not arzt:
        db_write(
            "INSERT INTO aerzte (user_id, vorname, nachname) VALUES (%s, %s, %s)",
            (current_user.id, current_user.username, "Auto")
        )
        arzt = db_read("SELECT arztid FROM aerzte WHERE user_id=%s", (current_user.id,))

    arztid = arzt[0]["arztid"]

    if request.method == "GET":
        return render_template("patient_new.html")

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

    pid = db_read("SELECT patientenid FROM patienten WHERE telefonnummer=%s", (telefon,))[0]["patientenid"]

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

    organs = request.form.getlist("organs")
    for organ in organs:
        db_write("INSERT INTO spenderorgane (verstorbenenid, organ) VALUES (%s,%s)", (vid, organ))

    return redirect(url_for("allocate", run=1))



@app.route("/doctor/allocate", methods=["GET", "POST"])
@login_required
@role_required("doctor", "admin")
def allocate():
    suggestions = []
    did_run = False

    run_now = (request.method == "POST") or (request.args.get("run") == "1")

    if run_now:
        did_run = True
        


        spender = db_read("""
            SELECT so.spenderorganid, so.organ,
                v.blutgruppe,
                v.alterskategorie,
                v.spital AS spender_spital,
                v.telefonnummerangehorige AS spender_telefon,
                NOW() AS spender_eingabedatum
            FROM spenderorgane so
            JOIN verstorbener v ON v.verstorbenenid = so.verstorbenenid
            LEFT JOIN zuteilung z ON z.spenderorganid = so.spenderorganid
                                AND z.status IN ('proposed','confirmed')
            WHERE z.zuteilungid IS NULL
        """)


        for s in spender:
            empfaenger_bgs = kompatible_empfaenger_blutgruppen(s["blutgruppe"])
            if not empfaenger_bgs:
                continue

            placeholders = ",".join(["%s"] * len(empfaenger_bgs))

            match = db_read(f"""
                SELECT ko.krankesorganid,
                    ko.dringlichkeit,
                    ko.created_at AS empfaenger_eingabedatum,
                    p.patientenid,
                    p.vorname,
                    p.nachname,
                    p.spital,
                    p.blutgruppe,
                    p.telefonnummer AS patient_telefon,
                    a.telefonnummer AS arzt_telefon
                FROM krankesorgan ko
                JOIN patienten p ON p.patientenid = ko.patientenid
                JOIN aerzte a ON a.arztid = p.arztid
                LEFT JOIN zuteilung z ON z.krankesorganid = ko.krankesorganid
                                    AND z.status IN ('proposed','confirmed')
                WHERE z.zuteilungid IS NULL
                AND ko.organ = %s
                AND p.blutgruppe IN ({placeholders})
                AND p.alterskategorie = %s
                ORDER BY
                LEAST(10, ko.dringlichkeit + FLOOR(TIMESTAMPDIFF(DAY, ko.created_at, NOW()) / 30)) DESC,
                ko.created_at ASC
                LIMIT 1
            """, tuple([s["organ"]] + empfaenger_bgs + [s["alterskategorie"]]))

            if match:
                db_write(
                    "INSERT INTO zuteilung (spenderorganid, krankesorganid, status) VALUES (%s, %s, 'proposed')",
                    (s["spenderorganid"], match[0]["krankesorganid"])
                )
                suggestions.append({"spender": s, "match": match[0]})
                # markiere als zugeteilt
                db_write("UPDATE spenderorgane SET status='allocated' WHERE spenderorganid=%s", (s["spenderorganid"],))
                db_write("UPDATE verstorbener v JOIN spenderorgane so ON so.verstorbenenid=v.verstorbenenid SET v.status='allocated' WHERE so.spenderorganid=%s", (s["spenderorganid"],))

                db_write("UPDATE krankesorgan SET status='allocated' WHERE krankesorganid=%s", (match[0]["krankesorganid"],))
                db_write("""
                UPDATE patienten p
                JOIN krankesorgan ko ON ko.patientenid=p.patientenid
                SET p.status='inactive'
                WHERE ko.krankesorganid=%s
                """, (match[0]["krankesorganid"],))


    auto_run = (request.args.get("run") == "1")
    return render_template("allocate.html", suggestions=suggestions, did_run=did_run, auto_run=auto_run)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = authenticate(request.form["username"], request.form["password"])

        if user:
            login_user(user)

            if getattr(user, "role", None) in ("doctor", "admin"):
                return redirect(url_for("doctor_home"))

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


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if getattr(current_user, "role", None) in ("doctor", "admin"):
        return redirect(url_for("doctor_home"))

    if request.method == "GET":
        todos = db_read("SELECT id, content, due FROM todos WHERE user_id=%s ORDER BY due", (current_user.id,))
        return render_template("main_page.html", todos=todos)

    content = request.form["contents"]
    due = request.form["due_at"]
    db_write("INSERT INTO todos (user_id, content, due) VALUES (%s, %s, %s)", (current_user.id, content, due,))
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
    tables_raw = db_read("SHOW TABLES")
    all_tables = [next(iter(row.values())) for row in tables_raw]

    selected_tables = []
    limit = 50
    results = {}

    if request.method == "POST":
        selected_tables = request.form.getlist("tables")

        limit_str = request.form.get("limit") or ""
        try:
            limit = int(limit_str)
        except ValueError:
            limit = 50

        if limit < 1:
            limit = 1
        elif limit > 1000:
            limit = 1000

        allowed = set(all_tables)

        for table in selected_tables:
            if table in allowed:
                rows = db_read(f"SELECT * FROM `{table}` LIMIT %s", (limit,))
                results[table] = rows

    return render_template(
        "dbexplorer.html",
        all_tables=all_tables,
        selected_tables=selected_tables,
        results=results,
        limit=limit,
    )


if __name__ == "__main__":
    app.run()
