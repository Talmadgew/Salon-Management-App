from __future__ import annotations

import base64
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "wierdaglow_full_suite.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-this-in-production")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


SERVICE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "sunbed": {
        "name": "Sunbed / UV Tanning",
        "category": "UV",
        "default_price": 120.00,
        "duration_minutes": 20,
        "intake": [
            "Recent harsh sun exposure or sunburn within the last 48 hours",
            "Pregnant or possible pregnancy",
            "History of skin cancer, suspicious lesions, or abnormal moles",
            "Photosensitivity or light-triggered condition",
            "Medication or products that may increase UV sensitivity",
            "Active skin condition or irritation relevant to UV exposure",
            "Relevant allergies",
            "Refuses protective eyewear",
        ],
        "acknowledgements": [
            "I understand UV tanning carries risks including burns, eye injury, premature ageing, and increased risk of skin cancer.",
            "I understand the maximum exposure time per session is 10 minutes and may not be exceeded.",
            "I understand I must avoid harsh direct sun exposure for at least 48 hours after a session.",
        ],
    },
    "nails": {
        "name": "Nail Services",
        "category": "Beauty",
        "default_price": 280.00,
        "duration_minutes": 90,
        "intake": [
            "Open wounds, cuts, infections, or fungal conditions on hands or feet",
            "Known allergies to gel, acrylic, acetone, glue, or other nail products",
            "Recent trauma to nails or surrounding skin",
            "Sensitive skin or previous adverse reactions to nail products",
        ],
        "acknowledgements": [
            "I confirm I have disclosed infections, allergies, and any condition affecting safe nail treatment.",
            "I understand results and wear time vary based on aftercare and my natural nail condition.",
        ],
    },
    "hair": {
        "name": "Hair Services",
        "category": "Hair",
        "default_price": 350.00,
        "duration_minutes": 120,
        "intake": [
            "Allergies or previous reactions to hair colour, bleach, relaxers, or treatment products",
            "Scalp irritation, sores, infections, or excessive sensitivity",
            "Recent chemical treatments that may affect safe application",
            "Pregnancy or medical condition relevant to chemical exposure",
        ],
        "acknowledgements": [
            "I understand hair colouring and chemical services may cause irritation or allergic reactions.",
            "I understand final colour or treatment outcome may vary based on my existing hair condition and history.",
        ],
    },
    "facials": {
        "name": "Facials",
        "category": "Skin",
        "default_price": 450.00,
        "duration_minutes": 75,
        "intake": [
            "Active acne treatment, chemical peels, retinoids, or medication affecting skin sensitivity",
            "Recent sunburn, laser, microneedling, or aggressive exfoliation",
            "Known allergies to skincare products or fragrances",
            "Active skin infections, sores, or unexplained rashes",
        ],
        "acknowledgements": [
            "I understand facial treatments may cause temporary redness, sensitivity, or breakouts.",
            "I will follow aftercare instructions and disclose all active products and treatments.",
        ],
    },
    "massage": {
        "name": "Massage Therapy",
        "category": "Wellness",
        "default_price": 500.00,
        "duration_minutes": 60,
        "intake": [
            "Pregnancy or possible pregnancy",
            "Recent injury, surgery, fracture, or severe pain",
            "Blood clot risk, cardiovascular condition, or uncontrolled high blood pressure",
            "Skin infections, contagious conditions, or fever",
        ],
        "acknowledgements": [
            "I understand massage is not a substitute for medical diagnosis or treatment.",
            "I will immediately report discomfort, pain, dizziness, or any adverse response during treatment.",
        ],
    },
    "waxing": {
        "name": "Waxing",
        "category": "Beauty",
        "default_price": 180.00,
        "duration_minutes": 45,
        "intake": [
            "Use of retinoids, isotretinoin, strong acids, or products that thin the skin",
            "Recent exfoliation, laser, sunburn, or skin irritation in the treatment area",
            "Diabetes, circulatory issues, or skin conditions affecting healing",
            "Known allergies to wax, resins, oils, or aftercare products",
        ],
        "acknowledgements": [
            "I understand waxing may cause redness, sensitivity, bruising, or skin lifting if contraindications are not disclosed.",
            "I will follow aftercare and avoid heat, friction, and harsh products after treatment.",
        ],
    },
    "brow_tint": {
        "name": "Eyebrow Tinting",
        "category": "Beauty",
        "default_price": 95.00,
        "duration_minutes": 30,
        "intake": [
            "Previous allergic reaction to tint, dye, peroxide, or related products",
            "Eye infection, irritation, recent eye procedure, or open skin around brows",
            "Sensitive skin or dermatitis in the brow area",
        ],
        "acknowledgements": [
            "I understand tinting products may cause irritation or allergic reactions.",
            "I consent to a patch test where required and will report previous reactions honestly.",
        ],
    },
    "tattoo": {
        "name": "Tattoo Services",
        "category": "Tattoo",
        "default_price": 650.00,
        "duration_minutes": 120,
        "intake": [
            "Blood clotting disorder, anticoagulant use, or abnormal bleeding history",
            "Pregnancy or breastfeeding",
            "Skin conditions, infections, or poor wound healing",
            "Relevant medical condition, medication, or allergy affecting tattoo safety",
        ],
        "acknowledgements": [
            "I understand tattooing breaks the skin and carries risks including infection, allergic reaction, and imperfect healing.",
            "I understand I am responsible for correct aftercare and that results vary by skin type and healing behaviour.",
        ],
    },
    "plasma_fibroblast": {
        "name": "Plasma Fibroblast Pen",
        "category": "Advanced Skin",
        "default_price": 1200.00,
        "duration_minutes": 90,
        "intake": [
            "Pregnancy or breastfeeding",
            "Pacemaker, epilepsy, diabetes, autoimmune condition, or poor healing",
            "Dark skin type or history of hyperpigmentation / keloid scarring",
            "Active skin infection, sunburn, recent fillers, botox, laser, or peels",
        ],
        "acknowledgements": [
            "I understand plasma fibroblast is an advanced aesthetic treatment with risks including swelling, scabbing, pigmentation change, and scarring.",
            "I understand strict aftercare and sun avoidance are mandatory.",
        ],
    },
    "skin_tightening": {
        "name": "Skin Tightening",
        "category": "Advanced Skin",
        "default_price": 900.00,
        "duration_minutes": 60,
        "intake": [
            "Pregnancy or breastfeeding",
            "Pacemaker, metal implants in treatment area, epilepsy, or serious medical condition",
            "Recent injectables, laser, peels, or skin procedures",
            "Active skin irritation, infection, or poor healing",
        ],
        "acknowledgements": [
            "I understand skin tightening results vary and may require multiple sessions.",
            "I understand temporary redness, swelling, and sensitivity may occur.",
        ],
    },
    "tattoo_removal": {
        "name": "Tattoo Removal",
        "category": "Advanced Skin",
        "default_price": 950.00,
        "duration_minutes": 60,
        "intake": [
            "Pregnancy or breastfeeding",
            "Photosensitivity, epilepsy, relevant medical conditions, or medication affecting treatment safety",
            "History of keloids, pigmentation issues, or poor wound healing",
            "Active infection, sunburn, or recent tanning in the treatment area",
        ],
        "acknowledgements": [
            "I understand tattoo removal may require multiple sessions and may not fully remove all pigment.",
            "I understand risks include pain, blistering, scarring, infection, and pigmentation changes.",
        ],
    },
}

COMMON_ACKS = [
    "I confirm that all answers and disclosures given by me are complete and truthful.",
    "I consent to the collection, storage, and processing of my personal information for treatment records, booking administration, billing, operational records, and legal compliance in terms of POPIA.",
    "To the extent permitted by South African law, I accept the inherent risks of this service and indemnify Wierdaglow Beauty Boutique and Qosnet (PTY) LTD against claims arising from my failure to disclose information or follow instructions, excluding gross negligence.",
]

PAYMENT_METHODS = ["cash", "card", "eft", "voucher", "mixed"]
BOOKING_STATUSES = ["booked", "confirmed", "completed", "cancelled", "no_show"]


@dataclass
class Assessment:
    status: str
    label: str
    reasons: list[str]
    warnings: list[str]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS staff_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    default_price REAL NOT NULL DEFAULT 0,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    id_number TEXT,
    phone TEXT NOT NULL,
    email TEXT,
    date_of_birth TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    medical_notes TEXT,
    popia_marketing_opt_in INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS treatment_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    service_code TEXT NOT NULL,
    service_name TEXT NOT NULL,
    service_date TEXT NOT NULL,
    staff_user_id INTEGER NOT NULL,
    staff_name TEXT NOT NULL,
    assessment_status TEXT NOT NULL,
    assessment_label TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    form_data_json TEXT NOT NULL,
    signature_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_user_id) REFERENCES staff_users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    client_name TEXT NOT NULL,
    phone TEXT,
    service_code TEXT NOT NULL,
    service_name TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    staff_user_id INTEGER,
    staff_name TEXT,
    status TEXT NOT NULL DEFAULT 'booked',
    notes TEXT,
    price_estimate REAL NOT NULL DEFAULT 0,
    created_by_user_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (staff_user_id) REFERENCES staff_users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES staff_users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT,
    name TEXT NOT NULL,
    category TEXT,
    unit_price REAL NOT NULL DEFAULT 0,
    stock_qty REAL NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL UNIQUE,
    client_id INTEGER,
    client_name TEXT,
    appointment_id INTEGER,
    staff_user_id INTEGER NOT NULL,
    staff_name TEXT NOT NULL,
    subtotal REAL NOT NULL,
    tax REAL NOT NULL,
    total REAL NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'unpaid',
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL,
    FOREIGN KEY (staff_user_id) REFERENCES staff_users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    product_id INTEGER,
    service_code TEXT,
    description TEXT NOT NULL,
    qty REAL NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    method TEXT NOT NULL,
    reference TEXT,
    paid_at TEXT NOT NULL,
    created_by_user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES staff_users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    detail TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES staff_users(id) ON DELETE SET NULL
);
"""


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA_SQL)
    now = utcnow()
    for code, service in SERVICE_DEFINITIONS.items():
        db.execute(
            """
            INSERT INTO services(code, name, category, default_price, duration_minutes, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                default_price = excluded.default_price,
                duration_minutes = excluded.duration_minutes,
                updated_at = excluded.updated_at
            """,
            (code, service["name"], service["category"], service["default_price"], service["duration_minutes"], now, now),
        )
    admin_exists = db.execute("SELECT id FROM staff_users WHERE username = ?", ("admin",)).fetchone()
    if not admin_exists:
        db.execute(
            """
            INSERT INTO staff_users(username, password_hash, full_name, role, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            ("admin", generate_password_hash("Admin@123"), "Salon Administrator", "admin", now),
        )
    product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if product_count == 0:
        starter_products = [
            ("NAIL-001", "Cuticle Oil", "Retail", 95.0, 12),
            ("HAIR-001", "Salon Shampoo", "Retail", 180.0, 8),
            ("SKIN-001", "Aftercare Gel", "Retail", 220.0, 10),
        ]
        for sku, name, category, price, qty in starter_products:
            db.execute(
                """
                INSERT INTO products(sku, name, category, unit_price, stock_qty, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (sku, name, category, price, qty, now, now),
            )
    db.commit()
    db.close()


@app.before_request
def load_current_user() -> None:
    g.user = None
    user_id = session.get("user_id")
    if user_id:
        g.user = get_db().execute(
            "SELECT id, username, full_name, role, active FROM staff_users WHERE id = ?",
            (user_id,),
        ).fetchone()


@app.context_processor
def inject_globals() -> dict[str, Any]:
    return {
        "current_user": g.get("user"),
        "service_definitions": SERVICE_DEFINITIONS,
        "payment_methods": PAYMENT_METHODS,
        "booking_statuses": BOOKING_STATUSES,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        if g.user["role"] != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def home():
    return redirect(url_for("dashboard")) if g.user else redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM staff_users WHERE username = ? AND active = 1",
            (username,),
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            write_audit(user["id"], "login", "staff_user", str(user["id"]), f"User {username} logged in")
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    write_audit(g.user["id"], "logout", "staff_user", str(g.user["id"]), f"User {g.user['username']} logged out")
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    counts = {
        "clients": db.execute("SELECT COUNT(*) AS c FROM clients").fetchone()["c"],
        "bookings": db.execute("SELECT COUNT(*) AS c FROM appointments WHERE status IN ('booked','confirmed')").fetchone()["c"],
        "invoices": db.execute("SELECT COUNT(*) AS c FROM invoices").fetchone()["c"],
        "outstanding": db.execute("SELECT COALESCE(SUM(total),0) AS c FROM invoices WHERE payment_status != 'paid'").fetchone()["c"],
    }
    todays_bookings = db.execute(
        """
        SELECT * FROM appointments
        WHERE substr(start_at, 1, 10) = ?
        ORDER BY start_at ASC
        LIMIT 12
        """,
        (today,),
    ).fetchall()
    recent_invoices = db.execute(
        "SELECT id, invoice_number, client_name, total, payment_status, created_at FROM invoices ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    recent_records = db.execute(
        """
        SELECT tr.id, tr.service_name, tr.service_date, tr.assessment_status,
               c.first_name, c.last_name
        FROM treatment_records tr
        JOIN clients c ON c.id = tr.client_id
        ORDER BY tr.created_at DESC
        LIMIT 8
        """
    ).fetchall()
    low_stock = db.execute(
        "SELECT * FROM products WHERE active = 1 AND stock_qty <= 3 ORDER BY stock_qty ASC, name ASC LIMIT 8"
    ).fetchall()
    return render_template(
        "dashboard.html",
        counts=counts,
        todays_bookings=todays_bookings,
        recent_invoices=recent_invoices,
        recent_records=recent_records,
        low_stock=low_stock,
        today=today,
    )


@app.route("/clients")
@login_required
def clients():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        rows = db.execute(
            """
            SELECT * FROM clients
            WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR id_number LIKE ? OR email LIKE ?
            ORDER BY updated_at DESC
            """,
            (like, like, like, like, like),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM clients ORDER BY updated_at DESC").fetchall()
    return render_template("clients.html", clients=rows, q=q)


@app.route("/clients/new", methods=["GET", "POST"])
@login_required
def client_new():
    if request.method == "POST":
        payload = client_payload_from_form(request.form)
        if not payload["first_name"] or not payload["last_name"] or not payload["phone"]:
            flash("First name, last name, and phone are mandatory.", "error")
            return render_template("client_form.html", client=payload, edit=False)
        now = utcnow()
        db = get_db()
        cur = db.execute(
            """
            INSERT INTO clients(
                first_name, last_name, id_number, phone, email, date_of_birth,
                emergency_contact_name, emergency_contact_phone, medical_notes,
                popia_marketing_opt_in, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["first_name"], payload["last_name"], payload["id_number"], payload["phone"], payload["email"], payload["date_of_birth"],
                payload["emergency_contact_name"], payload["emergency_contact_phone"], payload["medical_notes"],
                payload["popia_marketing_opt_in"], now, now,
            ),
        )
        db.commit()
        client_id = cur.lastrowid
        write_audit(g.user["id"], "create", "client", str(client_id), f"Created client {payload['first_name']} {payload['last_name']}")
        flash("Client created.", "success")
        return redirect(url_for("client_detail", client_id=client_id))
    return render_template("client_form.html", client={}, edit=False)


@app.route("/clients/<int:client_id>")
@login_required
def client_detail(client_id: int):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        flash("Client not found.", "error")
        return redirect(url_for("clients"))
    records = db.execute(
        """
        SELECT tr.*, su.full_name AS recorded_by
        FROM treatment_records tr
        JOIN staff_users su ON su.id = tr.staff_user_id
        WHERE tr.client_id = ?
        ORDER BY tr.service_date DESC, tr.created_at DESC
        """,
        (client_id,),
    ).fetchall()
    appointments = db.execute(
        "SELECT * FROM appointments WHERE client_id = ? ORDER BY start_at DESC LIMIT 20",
        (client_id,),
    ).fetchall()
    invoices = db.execute(
        "SELECT * FROM invoices WHERE client_id = ? ORDER BY created_at DESC LIMIT 20",
        (client_id,),
    ).fetchall()
    return render_template("client_detail.html", client=client, records=records, appointments=appointments, invoices=invoices)


@app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def client_edit(client_id: int):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        flash("Client not found.", "error")
        return redirect(url_for("clients"))
    if request.method == "POST":
        payload = client_payload_from_form(request.form)
        if not payload["first_name"] or not payload["last_name"] or not payload["phone"]:
            flash("First name, last name, and phone are mandatory.", "error")
            return render_template("client_form.html", client=payload, edit=True)
        db.execute(
            """
            UPDATE clients SET
                first_name = ?, last_name = ?, id_number = ?, phone = ?, email = ?, date_of_birth = ?,
                emergency_contact_name = ?, emergency_contact_phone = ?, medical_notes = ?,
                popia_marketing_opt_in = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload["first_name"], payload["last_name"], payload["id_number"], payload["phone"], payload["email"], payload["date_of_birth"],
                payload["emergency_contact_name"], payload["emergency_contact_phone"], payload["medical_notes"],
                payload["popia_marketing_opt_in"], utcnow(), client_id,
            ),
        )
        db.commit()
        write_audit(g.user["id"], "update", "client", str(client_id), f"Updated client {client_id}")
        flash("Client updated.", "success")
        return redirect(url_for("client_detail", client_id=client_id))
    return render_template("client_form.html", client=client, edit=True)


@app.route("/bookings")
@login_required
def bookings():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM appointments
        WHERE substr(start_at, 1, 10) = ?
        ORDER BY start_at ASC
        """,
        (selected_date,),
    ).fetchall()
    return render_template("bookings.html", bookings=rows, selected_date=selected_date)


@app.route("/bookings/new", methods=["GET", "POST"])
@login_required
def booking_new():
    db = get_db()
    clients = db.execute("SELECT id, first_name, last_name, phone FROM clients ORDER BY first_name, last_name").fetchall()
    staff = db.execute("SELECT id, full_name FROM staff_users WHERE active = 1 ORDER BY full_name").fetchall()
    if request.method == "POST":
        payload = booking_payload_from_form(request.form)
        error = validate_booking_payload(payload)
        if error:
            flash(error, "error")
            return render_template("booking_form.html", booking=payload, clients=clients, staff=staff, edit=False)
        if booking_overlap_exists(payload):
            flash("That staff member already has an overlapping booking.", "error")
            return render_template("booking_form.html", booking=payload, clients=clients, staff=staff, edit=False)
        now = utcnow()
        db.execute(
            """
            INSERT INTO appointments(
                client_id, client_name, phone, service_code, service_name, start_at, end_at, duration_minutes,
                staff_user_id, staff_name, status, notes, price_estimate, created_by_user_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["client_id"], payload["client_name"], payload["phone"], payload["service_code"], payload["service_name"],
                payload["start_at"], payload["end_at"], payload["duration_minutes"], payload["staff_user_id"], payload["staff_name"],
                payload["status"], payload["notes"], payload["price_estimate"], g.user["id"], now, now,
            ),
        )
        db.commit()
        write_audit(g.user["id"], "create", "appointment", None, f"Booked {payload['service_name']} for {payload['client_name']}")
        flash("Booking created.", "success")
        return redirect(url_for("bookings", date=payload["start_at"][:10]))
    prefill = {
        "service_code": request.args.get("service_code", ""),
        "start_date": request.args.get("date", date.today().isoformat()),
        "start_time": request.args.get("time", "09:00"),
        "status": "booked",
    }
    return render_template("booking_form.html", booking=prefill, clients=clients, staff=staff, edit=False)


@app.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
@login_required
def booking_edit(booking_id: int):
    db = get_db()
    booking = db.execute("SELECT * FROM appointments WHERE id = ?", (booking_id,)).fetchone()
    if booking is None:
        flash("Booking not found.", "error")
        return redirect(url_for("bookings"))
    clients = db.execute("SELECT id, first_name, last_name, phone FROM clients ORDER BY first_name, last_name").fetchall()
    staff = db.execute("SELECT id, full_name FROM staff_users WHERE active = 1 ORDER BY full_name").fetchall()
    if request.method == "POST":
        payload = booking_payload_from_form(request.form)
        error = validate_booking_payload(payload)
        if error:
            flash(error, "error")
            return render_template("booking_form.html", booking=payload, clients=clients, staff=staff, edit=True)
        if booking_overlap_exists(payload, exclude_id=booking_id):
            flash("That staff member already has an overlapping booking.", "error")
            return render_template("booking_form.html", booking=payload, clients=clients, staff=staff, edit=True)
        db.execute(
            """
            UPDATE appointments SET
                client_id=?, client_name=?, phone=?, service_code=?, service_name=?, start_at=?, end_at=?, duration_minutes=?,
                staff_user_id=?, staff_name=?, status=?, notes=?, price_estimate=?, updated_at=?
            WHERE id=?
            """,
            (
                payload["client_id"], payload["client_name"], payload["phone"], payload["service_code"], payload["service_name"],
                payload["start_at"], payload["end_at"], payload["duration_minutes"], payload["staff_user_id"], payload["staff_name"],
                payload["status"], payload["notes"], payload["price_estimate"], utcnow(), booking_id,
            ),
        )
        db.commit()
        write_audit(g.user["id"], "update", "appointment", str(booking_id), f"Updated booking {booking_id}")
        flash("Booking updated.", "success")
        return redirect(url_for("bookings", date=payload["start_at"][:10]))
    payload = booking_to_form_payload(booking)
    return render_template("booking_form.html", booking=payload, clients=clients, staff=staff, edit=True)


@app.route("/bookings/<int:booking_id>/status", methods=["POST"])
@login_required
def booking_status(booking_id: int):
    status = request.form.get("status", "booked")
    if status not in BOOKING_STATUSES:
        flash("Invalid booking status.", "error")
        return redirect(url_for("bookings"))
    db = get_db()
    booking = db.execute("SELECT * FROM appointments WHERE id = ?", (booking_id,)).fetchone()
    if booking is None:
        flash("Booking not found.", "error")
        return redirect(url_for("bookings"))
    db.execute("UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?", (status, utcnow(), booking_id))
    db.commit()
    write_audit(g.user["id"], "status", "appointment", str(booking_id), f"Set booking status to {status}")
    flash("Booking status updated.", "success")
    return redirect(url_for("bookings", date=booking["start_at"][:10]))


@app.route("/products")
@login_required
def products():
    rows = get_db().execute("SELECT * FROM products ORDER BY active DESC, name ASC").fetchall()
    return render_template("products.html", products=rows)


@app.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    if request.method == "POST":
        payload = product_payload_from_form(request.form)
        if not payload["name"]:
            flash("Product name is required.", "error")
            return render_template("product_form.html", product=payload, edit=False)
        db = get_db()
        db.execute(
            """
            INSERT INTO products(sku, name, category, unit_price, stock_qty, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["sku"], payload["name"], payload["category"], payload["unit_price"], payload["stock_qty"],
                payload["active"], utcnow(), utcnow(),
            ),
        )
        db.commit()
        flash("Product created.", "success")
        return redirect(url_for("products"))
    return render_template("product_form.html", product={}, edit=False)


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id: int):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("products"))
    if request.method == "POST":
        payload = product_payload_from_form(request.form)
        if not payload["name"]:
            flash("Product name is required.", "error")
            return render_template("product_form.html", product=payload, edit=True)
        db.execute(
            """
            UPDATE products SET sku=?, name=?, category=?, unit_price=?, stock_qty=?, active=?, updated_at=?
            WHERE id=?
            """,
            (
                payload["sku"], payload["name"], payload["category"], payload["unit_price"], payload["stock_qty"], payload["active"], utcnow(), product_id,
            ),
        )
        db.commit()
        flash("Product updated.", "success")
        return redirect(url_for("products"))
    return render_template("product_form.html", product=product, edit=True)


@app.route("/pos")
@login_required
def invoice_list():
    rows = get_db().execute(
        "SELECT id, invoice_number, client_name, total, payment_status, created_at FROM invoices ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    return render_template("invoices.html", invoices=rows)


@app.route("/pos/new", methods=["GET", "POST"])
@login_required
def invoice_new():
    db = get_db()
    clients = db.execute("SELECT id, first_name, last_name FROM clients ORDER BY first_name, last_name").fetchall()
    appointments = db.execute(
        "SELECT id, client_name, service_name, start_at, status, price_estimate FROM appointments ORDER BY start_at DESC LIMIT 100"
    ).fetchall()
    products = db.execute("SELECT id, sku, name, unit_price, stock_qty FROM products WHERE active = 1 ORDER BY name").fetchall()
    if request.method == "POST":
        payload, lines, stock_error = invoice_payload_from_form(request.form)
        if stock_error:
            flash(stock_error, "error")
            return render_template("invoice_form.html", payload=payload, lines=lines, clients=clients, appointments=appointments, products=products)
        if not lines:
            flash("Add at least one invoice line.", "error")
            return render_template("invoice_form.html", payload=payload, lines=lines, clients=clients, appointments=appointments, products=products)
        subtotal = round(sum(line["line_total"] for line in lines), 2)
        tax = round(payload["tax_rate"] * subtotal / 100, 2)
        total = round(subtotal + tax, 2)
        now = utcnow()
        invoice_number = next_invoice_number(db)
        cur = db.execute(
            """
            INSERT INTO invoices(
                invoice_number, client_id, client_name, appointment_id, staff_user_id, staff_name,
                subtotal, tax, total, payment_status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_number, payload["client_id"], payload["client_name"], payload["appointment_id"], g.user["id"], g.user["full_name"],
                subtotal, tax, total, "unpaid", payload["notes"], now, now,
            ),
        )
        invoice_id = cur.lastrowid
        for line in lines:
            db.execute(
                """
                INSERT INTO invoice_items(invoice_id, item_type, product_id, service_code, description, qty, unit_price, line_total, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id, line["item_type"], line["product_id"], line["service_code"], line["description"],
                    line["qty"], line["unit_price"], line["line_total"], now,
                ),
            )
            if line["product_id"]:
                db.execute("UPDATE products SET stock_qty = stock_qty - ?, updated_at = ? WHERE id = ?", (line["qty"], now, line["product_id"]))
        db.commit()
        write_audit(g.user["id"], "create", "invoice", str(invoice_id), f"Created invoice {invoice_number}")
        flash("Invoice created. Capture payment next.", "success")
        return redirect(url_for("invoice_detail", invoice_id=invoice_id))
    payload = {"tax_rate": "15", "notes": ""}
    return render_template("invoice_form.html", payload=payload, lines=[], clients=clients, appointments=appointments, products=products)


@app.route("/pos/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id: int):
    db = get_db()
    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if invoice is None:
        flash("Invoice not found.", "error")
        return redirect(url_for("invoice_list"))
    items = db.execute("SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id", (invoice_id,)).fetchall()
    payments = db.execute("SELECT * FROM payments WHERE invoice_id = ? ORDER BY paid_at DESC, id DESC", (invoice_id,)).fetchall()
    paid_total = sum(p["amount"] for p in payments)
    balance = round(invoice["total"] - paid_total, 2)
    client = None
    if invoice["client_id"]:
        client = db.execute("SELECT * FROM clients WHERE id = ?", (invoice["client_id"],)).fetchone()
    return render_template("invoice_detail.html", invoice=invoice, items=items, payments=payments, paid_total=paid_total, balance=balance, client=client)


@app.route("/pos/<int:invoice_id>/pay", methods=["POST"])
@login_required
def invoice_pay(invoice_id: int):
    db = get_db()
    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if invoice is None:
        flash("Invoice not found.", "error")
        return redirect(url_for("invoice_list"))
    amount = safe_float(request.form.get("amount"))
    method = request.form.get("method", "card")
    reference = request.form.get("reference", "").strip()
    if amount <= 0:
        flash("Payment amount must be greater than zero.", "error")
        return redirect(url_for("invoice_detail", invoice_id=invoice_id))
    if method not in PAYMENT_METHODS:
        flash("Invalid payment method.", "error")
        return redirect(url_for("invoice_detail", invoice_id=invoice_id))
    now = utcnow()
    db.execute(
        "INSERT INTO payments(invoice_id, amount, method, reference, paid_at, created_by_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (invoice_id, amount, method, reference, now, g.user["id"], now),
    )
    paid_total = db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE invoice_id = ?", (invoice_id,)).fetchone()[0]
    status = "paid" if round(paid_total + amount, 2) >= round(invoice["total"], 2) else "partial"
    db.execute("UPDATE invoices SET payment_status = ?, updated_at = ? WHERE id = ?", (status, now, invoice_id))
    db.commit()
    write_audit(g.user["id"], "payment", "invoice", str(invoice_id), f"Captured {amount:.2f} payment via {method}")
    flash("Payment captured.", "success")
    return redirect(url_for("invoice_detail", invoice_id=invoice_id))


@app.route("/clients/<int:client_id>/records/new", methods=["GET", "POST"])
@login_required
def record_new(client_id: int):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        flash("Client not found.", "error")
        return redirect(url_for("clients"))

    if request.method == "POST":
        payload = request.form.to_dict(flat=True)
        service_code = payload.get("service_code", "").strip()
        service_date = payload.get("service_date", today_iso())
        if service_code not in SERVICE_DEFINITIONS:
            flash("Select a valid service.", "error")
            return render_template("record_form.html", client=client, today=today_iso(), payload=payload)
        service_name = SERVICE_DEFINITIONS[service_code]["name"]

        form_data = {
            "intake": {str(i): bool(request.form.get(f"intake_{i}")) for i in range(len(SERVICE_DEFINITIONS[service_code]["intake"]))},
            "acknowledgements": {
                **{f"service_{i}": bool(request.form.get(f"service_ack_{i}")) for i in range(len(SERVICE_DEFINITIONS[service_code]["acknowledgements"]))},
                **{f"common_{i}": bool(request.form.get(f"common_ack_{i}")) for i in range(len(COMMON_ACKS))},
            },
            "general_notes": payload.get("general_notes", "").strip(),
            "staff_notes": payload.get("staff_notes", "").strip(),
            "typed_name": payload.get("typed_name", "").strip(),
            "sunbed": {
                "minutes_requested": safe_int(payload.get("minutes_requested")),
                "previous_session_date": payload.get("previous_session_date", "").strip(),
                "skin_type": payload.get("skin_type", "").strip(),
            },
        }

        if not form_data["typed_name"]:
            flash("Client typed full name is required.", "error")
            return render_template("record_form.html", client=client, today=today_iso(), payload=payload)

        signature_data = payload.get("signature_data", "")
        signature_path = None
        if signature_data:
            try:
                signature_path = store_signature(signature_data)
            except ValueError as exc:
                flash(str(exc), "error")
                return render_template("record_form.html", client=client, today=today_iso(), payload=payload)

        assessment = assess_service(client, service_code, service_date, form_data)
        now = utcnow()
        cur = db.execute(
            """
            INSERT INTO treatment_records(
                client_id, service_code, service_name, service_date, staff_user_id, staff_name,
                assessment_status, assessment_label, reasons_json, warnings_json,
                form_data_json, signature_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id, service_code, service_name, service_date, g.user["id"], g.user["full_name"], assessment.status,
                assessment.label, json.dumps(assessment.reasons), json.dumps(assessment.warnings), json.dumps(form_data), signature_path, now, now,
            ),
        )
        db.execute("UPDATE clients SET updated_at = ? WHERE id = ?", (now, client_id))
        db.commit()
        record_id = cur.lastrowid
        write_audit(g.user["id"], "create", "treatment_record", str(record_id), f"Created {service_name} record for client {client_id}")
        flash("Treatment record saved." if assessment.status == "safe" else f"Record saved with status: {assessment.label}", "success" if assessment.status == "safe" else "warning")
        return redirect(url_for("record_print", record_id=record_id))

    return render_template("record_form.html", client=client, today=today_iso(), payload={})


@app.route("/records/<int:record_id>/print")
@login_required
def record_print(record_id: int):
    db = get_db()
    record = db.execute(
        """
        SELECT tr.*, c.first_name, c.last_name, c.id_number, c.phone, c.email, c.date_of_birth,
               c.emergency_contact_name, c.emergency_contact_phone, c.medical_notes
        FROM treatment_records tr
        JOIN clients c ON c.id = tr.client_id
        WHERE tr.id = ?
        """,
        (record_id,),
    ).fetchone()
    if record is None:
        flash("Record not found.", "error")
        return redirect(url_for("dashboard"))
    form_data = json.loads(record["form_data_json"])
    reasons = json.loads(record["reasons_json"])
    warnings = json.loads(record["warnings_json"])
    signature_exists = bool(record["signature_path"]) and (BASE_DIR / record["signature_path"]).exists()
    return render_template(
        "record_print.html",
        record=record,
        form_data=form_data,
        reasons=reasons,
        warnings=warnings,
        service=SERVICE_DEFINITIONS[record["service_code"]],
        common_acks=COMMON_ACKS,
        signature_exists=signature_exists,
    )


@app.route("/staff")
@admin_required
def staff_list():
    rows = get_db().execute("SELECT id, username, full_name, role, active, created_at FROM staff_users ORDER BY full_name").fetchall()
    return render_template("staff_list.html", staff=rows)


@app.route("/staff/new", methods=["GET", "POST"])
@admin_required
def staff_new():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "staff").strip()
        if not username or not password or not full_name:
            flash("Username, password, and full name are mandatory.", "error")
            return render_template("staff_form.html", staff=request.form, edit=False)
        if role not in {"admin", "staff"}:
            flash("Invalid role.", "error")
            return render_template("staff_form.html", staff=request.form, edit=False)
        try:
            cur = get_db().execute(
                "INSERT INTO staff_users(username, password_hash, full_name, role, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (username, generate_password_hash(password), full_name, role, utcnow()),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
            return render_template("staff_form.html", staff=request.form, edit=False)
        write_audit(g.user["id"], "create", "staff_user", str(cur.lastrowid), f"Created staff user {username}")
        flash("Staff user created.", "success")
        return redirect(url_for("staff_list"))
    return render_template("staff_form.html", staff={}, edit=False)


@app.route("/staff/<int:user_id>/toggle", methods=["POST"])
@admin_required
def staff_toggle(user_id: int):
    if user_id == g.user["id"]:
        flash("You cannot deactivate your own account here.", "error")
        return redirect(url_for("staff_list"))
    db = get_db()
    user = db.execute("SELECT id, username, active FROM staff_users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        flash("Staff user not found.", "error")
        return redirect(url_for("staff_list"))
    new_active = 0 if user["active"] else 1
    db.execute("UPDATE staff_users SET active = ? WHERE id = ?", (new_active, user_id))
    db.commit()
    write_audit(g.user["id"], "toggle", "staff_user", str(user_id), f"Set active={new_active} for {user['username']}")
    flash("Staff status updated.", "success")
    return redirect(url_for("staff_list"))


@app.route("/audit")
@admin_required
def audit_log():
    rows = get_db().execute(
        """
        SELECT a.*, s.full_name
        FROM audit_log a
        LEFT JOIN staff_users s ON s.id = a.user_id
        ORDER BY a.created_at DESC
        LIMIT 200
        """
    ).fetchall()
    return render_template("audit_log.html", entries=rows)


@app.route("/api/services")
@login_required
def api_services():
    return jsonify({"services": SERVICE_DEFINITIONS, "common_acknowledgements": COMMON_ACKS})


@app.route("/api/products")
@login_required
def api_products():
    rows = get_db().execute("SELECT id, sku, name, unit_price, stock_qty FROM products WHERE active = 1 ORDER BY name").fetchall()
    return jsonify({"products": [dict(r) for r in rows]})


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


def assess_service(client: sqlite3.Row, service_code: str, service_date: str, form_data: dict[str, Any]) -> Assessment:
    reasons: list[str] = []
    warnings: list[str] = []
    age = calculate_age(client["date_of_birth"], service_date) if client["date_of_birth"] else None
    intake = form_data["intake"]
    if age is not None and age < 18:
        reasons.append("Client is under 18.")

    if service_code == "sunbed":
        if intake.get("0"):
            reasons.append("Recent harsh sun exposure or sunburn disclosed within 48 hours.")
        if intake.get("1"):
            reasons.append("Pregnancy disclosed.")
        if intake.get("2"):
            reasons.append("History of skin cancer or suspicious lesions disclosed.")
        if intake.get("3"):
            reasons.append("Photosensitivity disclosed.")
        if intake.get("7"):
            reasons.append("Client refuses protective eyewear.")
        if intake.get("4"):
            warnings.append("Medication or products affecting UV sensitivity disclosed. Manual review required.")
        if intake.get("5"):
            warnings.append("Active skin condition disclosed. Manual review required.")
        if form_data["sunbed"].get("skin_type") == "I":
            reasons.append("Fitzpatrick Type I flagged as unsafe by policy.")
        minutes = form_data["sunbed"].get("minutes_requested") or 0
        if minutes > 10:
            reasons.append("Requested session exceeds 10-minute maximum.")
        previous_session_date = form_data["sunbed"].get("previous_session_date")
        if previous_session_date and hours_between(previous_session_date, service_date) < 48:
            reasons.append("Previous session falls inside the 48-hour restriction window.")
        last_record = get_db().execute(
            "SELECT service_date FROM treatment_records WHERE client_id = ? AND service_code = 'sunbed' ORDER BY service_date DESC, created_at DESC LIMIT 1",
            (client["id"],),
        ).fetchone()
        if last_record and hours_between(last_record["service_date"], service_date) < 48:
            reasons.append("Last logged sunbed session falls inside the 48-hour restriction window.")
    else:
        high_risk_service_codes = {"plasma_fibroblast", "tattoo_removal", "skin_tightening", "tattoo"}
        if intake.get("0") and service_code in high_risk_service_codes:
            reasons.append("Primary high-risk contraindication disclosed.")
        if any(intake.values()):
            warnings.append("Contraindications disclosed. Staff must manually review suitability before treatment.")

    if reasons:
        return Assessment("blocked", "Unsafe / refuse service", reasons, warnings)
    if warnings:
        return Assessment("caution", "Caution / manual review", reasons, warnings)
    return Assessment("safe", "Suitable based on captured data", reasons, warnings)


def client_payload_from_form(form: Any) -> dict[str, Any]:
    return {
        "first_name": form.get("first_name", "").strip(),
        "last_name": form.get("last_name", "").strip(),
        "id_number": form.get("id_number", "").strip(),
        "phone": form.get("phone", "").strip(),
        "email": form.get("email", "").strip(),
        "date_of_birth": form.get("date_of_birth", "").strip(),
        "emergency_contact_name": form.get("emergency_contact_name", "").strip(),
        "emergency_contact_phone": form.get("emergency_contact_phone", "").strip(),
        "medical_notes": form.get("medical_notes", "").strip(),
        "popia_marketing_opt_in": 1 if form.get("popia_marketing_opt_in") else 0,
    }


def booking_payload_from_form(form: Any) -> dict[str, Any]:
    db = get_db()
    client_id_raw = form.get("client_id", "").strip()
    client_id = int(client_id_raw) if client_id_raw.isdigit() else None
    client_name = form.get("walkin_name", "").strip()
    phone = form.get("walkin_phone", "").strip()
    if client_id:
        client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if client:
            client_name = f"{client['first_name']} {client['last_name']}"
            phone = client["phone"]
    service_code = form.get("service_code", "").strip()
    service_def = SERVICE_DEFINITIONS.get(service_code, {})
    service_name = service_def.get("name", "")
    duration = safe_int(form.get("duration_minutes")) or safe_int(service_def.get("duration_minutes", 60))
    start_date = form.get("start_date", today_iso())
    start_time = form.get("start_time", "09:00")
    start_dt = parse_local_datetime(f"{start_date} {start_time}")
    end_dt = start_dt + timedelta(minutes=duration)
    staff_user_id = safe_int(form.get("staff_user_id")) or None
    staff_name = None
    if staff_user_id:
        row = db.execute("SELECT full_name FROM staff_users WHERE id = ?", (staff_user_id,)).fetchone()
        staff_name = row["full_name"] if row else None
    return {
        "client_id": client_id,
        "client_name": client_name,
        "phone": phone,
        "service_code": service_code,
        "service_name": service_name,
        "start_date": start_date,
        "start_time": start_time,
        "start_at": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_at": end_dt.strftime("%Y-%m-%d %H:%M"),
        "duration_minutes": duration,
        "staff_user_id": staff_user_id,
        "staff_name": staff_name,
        "status": form.get("status", "booked"),
        "notes": form.get("notes", "").strip(),
        "price_estimate": safe_float(form.get("price_estimate") or service_def.get("default_price", 0)),
    }


def booking_to_form_payload(booking: sqlite3.Row) -> dict[str, Any]:
    dt = parse_local_datetime(booking["start_at"])
    return {
        "client_id": booking["client_id"] or "",
        "walkin_name": "" if booking["client_id"] else booking["client_name"],
        "walkin_phone": "" if booking["client_id"] else (booking["phone"] or ""),
        "service_code": booking["service_code"],
        "duration_minutes": booking["duration_minutes"],
        "staff_user_id": booking["staff_user_id"] or "",
        "status": booking["status"],
        "price_estimate": booking["price_estimate"],
        "notes": booking["notes"] or "",
        "start_date": dt.strftime("%Y-%m-%d"),
        "start_time": dt.strftime("%H:%M"),
    }


def validate_booking_payload(payload: dict[str, Any]) -> str | None:
    if payload["service_code"] not in SERVICE_DEFINITIONS:
        return "Select a valid service."
    if not payload["client_name"]:
        return "Choose a client or enter a walk-in client name."
    if payload["status"] not in BOOKING_STATUSES:
        return "Invalid booking status."
    if payload["duration_minutes"] <= 0:
        return "Duration must be greater than zero."
    if not payload["staff_user_id"]:
        return "Assign a staff member."
    return None


def booking_overlap_exists(payload: dict[str, Any], exclude_id: int | None = None) -> bool:
    db = get_db()
    query = """
        SELECT id FROM appointments
        WHERE staff_user_id = ?
          AND status IN ('booked', 'confirmed')
          AND start_at < ?
          AND end_at > ?
    """
    params: list[Any] = [payload["staff_user_id"], payload["end_at"], payload["start_at"]]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    return db.execute(query, params).fetchone() is not None


def product_payload_from_form(form: Any) -> dict[str, Any]:
    return {
        "sku": form.get("sku", "").strip(),
        "name": form.get("name", "").strip(),
        "category": form.get("category", "").strip(),
        "unit_price": safe_float(form.get("unit_price")),
        "stock_qty": safe_float(form.get("stock_qty")),
        "active": 1 if form.get("active") else 0,
    }


def invoice_payload_from_form(form: Any) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    db = get_db()
    client_id = safe_int(form.get("client_id")) or None
    client_name = form.get("walkin_name", "").strip()
    if client_id:
        row = db.execute("SELECT first_name, last_name FROM clients WHERE id = ?", (client_id,)).fetchone()
        if row:
            client_name = f"{row['first_name']} {row['last_name']}"
    appointment_id = safe_int(form.get("appointment_id")) or None
    payload = {
        "client_id": client_id,
        "client_name": client_name,
        "appointment_id": appointment_id,
        "tax_rate": safe_float(form.get("tax_rate", 15)),
        "notes": form.get("notes", "").strip(),
    }
    lines: list[dict[str, Any]] = []
    idx = 0
    stock_error = None
    while True:
        marker = form.get(f"line_item_type_{idx}")
        if marker is None:
            break
        item_type = marker.strip() or "manual"
        description = form.get(f"line_description_{idx}", "").strip()
        qty = safe_float(form.get(f"line_qty_{idx}"))
        unit_price = safe_float(form.get(f"line_price_{idx}"))
        product_id = safe_int(form.get(f"line_product_id_{idx}")) or None
        service_code = form.get(f"line_service_code_{idx}", "").strip() or None
        if qty <= 0 or not description:
            idx += 1
            continue
        if product_id:
            product = db.execute("SELECT name, stock_qty FROM products WHERE id = ?", (product_id,)).fetchone()
            if product and qty > float(product["stock_qty"]):
                stock_error = f"Insufficient stock for {product['name']}."
                break
        line_total = round(qty * unit_price, 2)
        lines.append(
            {
                "item_type": item_type,
                "product_id": product_id,
                "service_code": service_code,
                "description": description,
                "qty": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )
        idx += 1
    return payload, lines, stock_error


def next_invoice_number(db: sqlite3.Connection) -> str:
    prefix = date.today().strftime("INV%Y%m")
    row = db.execute("SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE ?", (f"{prefix}%",)).fetchone()
    seq = int(row[0]) + 1
    return f"{prefix}-{seq:04d}"


def store_signature(data_url: str) -> str:
    if not data_url.startswith("data:image/png;base64,"):
        raise ValueError("Invalid signature image format.")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    filename = f"sig_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.png"
    path = UPLOAD_DIR / filename
    path.write_bytes(raw)
    return f"uploads/{filename}"


def write_audit(user_id: int | None, action: str, entity_type: str, entity_id: str | None, detail: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO audit_log(user_id, action, entity_type, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, action, entity_type, entity_id, detail, utcnow()),
    )
    db.commit()


def utcnow() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def today_iso() -> str:
    return date.today().isoformat()


def calculate_age(date_of_birth: str, effective_date: str) -> int | None:
    try:
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        ref = datetime.strptime(effective_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def hours_between(start_date: str, end_date: str) -> float:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    return (end_dt - start_dt).total_seconds() / 3600


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def parse_local_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime value: {value}")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
