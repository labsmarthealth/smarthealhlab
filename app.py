# app.py — full regenerated, cleaned, and fixed
import os
import json
import hmac
import hashlib
import requests
from datetime import datetime
from flask import Flask, request, redirect, render_template, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from openpyxl import Workbook
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from flask_cors import CORS
import random

# ---------------- Config ----------------
load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:*", "http://localhost:*"]}})


app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# Admin & SMTP
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SMTP_SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

# WhatsApp
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v17.0")
TEST_PHONE_NUMBER = os.getenv("WHATSAPP_TEST_NUMBER")

os.makedirs("exports", exist_ok=True)

# ---------------- Models ----------------
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_type = db.Column(db.String(50), nullable=False)
    test_name = db.Column(db.String(200))
    items_json = db.Column(db.Text)
    total_amount = db.Column(db.Float)
    customer_name = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(200))
    message = db.Column(db.Text)
    location = db.Column(db.String(100))
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    preferred_date = db.Column(db.String(20))
    preferred_time = db.Column(db.String(20))
    payment_mode = db.Column(db.String(20))
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# ---------------- Email Helpers ----------------
def send_email(to_email, subject, body_text, html_content=None, sender_name="HealthLab Bangalore"):
    if not (SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD):
        print("[EMAIL] Skipped: SMTP not configured")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((sender_name, SMTP_SENDER_EMAIL))
        msg["To"] = to_email

        part1 = MIMEText(body_text or subject, "plain")
        msg.attach(part1)
        if html_content:
            part2 = MIMEText(html_content, "html")
            msg.attach(part2)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_SENDER_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_SENDER_EMAIL, [to_email], msg.as_string())
        print(f"[EMAIL] Sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL] Error: {e}")

def render_booking_text(booking):
    items = booking.items_json or ""
    if booking.booking_type == "manual":
        items = booking.test_name or ""
    return f"""Hi {booking.customer_name},

Your booking for {items} has been successfully confirmed.
Order ID: {booking.id}

Thank you for choosing us.
We look forward to serving you.
"""

def normalize_phone(number: str) -> str:
    if not number:
        return number
    number = str(number).strip().replace("+", "").replace(" ", "")
    if number.startswith("0") and len(number) == 11:
        number = number[1:]
    if not number.startswith("91"):
        number = "91" + number
    return number

# ---------------- WhatsApp Helpers ----------------
def send_whatsapp(to_number, message):
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        print("[WHATSAPP] Skipped: Token not configured")
        return
    to_number = normalize_phone(to_number)
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": message}}
    try:
        resp = requests.post(url, headers=headers, json=payload)
        print(f"[WHATSAPP] Sent to {to_number}: {resp.json()}")
        return resp.json()
    except Exception as e:
        print(f"[WHATSAPP] Error: {e}")
        return {"error": str(e)}

def send_template_message(to_number, template_name, language="en_US", components=None):
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        print("[WHATSAPP] Skipped: Token not configured")
        return
    to_number = normalize_phone(to_number)
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "template",
               "template": {"name": template_name, "language": {"code": language}}}
    if components:
        payload["template"]["components"] = components
    try:
        r = requests.post(url, headers=headers, json=payload)
        print(f"[WHATSAPP] Template sent to {to_number}: {r.status_code} {r.text}")
        if r.status_code != 200:
            return {"error": r.text}
        return r.json()
    except Exception as e:
        print(f"[WHATSAPP] Template send error: {e}")
        return {"error": str(e)}
    

def send_order_confirmation_whatsapp(booking):
    """
    Send WhatsApp order confirmation using template 'order_confirmation'.
    Placeholders: {{1}} = customer_name, {{2}} = order_id, {{3}} = status
    """
    template_name = os.getenv("WHATSAPP_TEMPLATE_NAME", "order_confirmation")
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": booking.customer_name or "Customer"},
                {"type": "text", "text": str(booking.id)},
                {"type": "text", "text": booking.status or "Confirmed"}
            ]
        }
    ]
    return send_template_message(
        to_number=booking.phone,
        template_name=template_name,
        components=components
    )


# ---------------- Routes ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = Admin.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("orders"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# OTP / Password
otp_storage = {}

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        old_pass = request.form.get("old_password")
        new_pass = request.form.get("new_password")
        user = Admin.query.filter_by(email=ADMIN_EMAIL).first()
        if user and check_password_hash(user.password_hash, old_pass):
            user.password_hash = generate_password_hash(new_pass)
            db.session.commit()
            flash("Password updated successfully!", "success")
            return redirect(url_for("login"))
        flash("Old password is incorrect.", "error")
    return render_template("forgot_password.html")

@app.route("/request-otp", methods=["GET", "POST"])
def request_otp():
    if request.method == "POST":
        otp = str(random.randint(100000, 999999))
        otp_storage["code"] = otp
        send_email(ADMIN_EMAIL, "🔐 Your OTP Code", f"Your OTP is {otp}")
        flash("OTP sent to your email.", "info")
        return redirect(url_for("verify_otp"))
    return render_template("request_otp.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        new_pass = request.form.get("new_password")
        if otp_storage.get("code") == entered_otp:
            user = Admin.query.filter_by(email=ADMIN_EMAIL).first()
            if user:
                user.password_hash = generate_password_hash(new_pass)
                db.session.commit()
                otp_storage.pop("code", None)
                flash("Password reset successfully via OTP!", "success")
                return redirect(url_for("login"))
        flash("Invalid OTP", "error")
    return render_template("verify_otp.html")

# Admin orders
@app.route("/admin/orders")
@login_required
def orders():
    rows = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template("orders.html", rows=rows)

@app.route("/admin/confirm/<int:booking_id>", methods=["POST"])
@login_required
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.booking_type == "checkout" and (booking.payment_mode or "").lower() == "upi":
        booking.status = "Done" if booking.status != "Payment Pending Verification" else "Done"
    else:
        booking.status = "Done"
    db.session.commit()
    # Email
# WhatsApp
    if booking.phone:
        resp = send_order_confirmation_whatsapp(booking)

        # Fallback if template fails
        if not resp or (isinstance(resp, dict) and resp.get("error")):
            send_whatsapp(
                booking.phone,
                f"Hi {booking.customer_name}, your booking (ID {booking.id}) is now marked as {booking.status or 'Done'}. ✅"
            )


    return redirect(url_for("orders"))


# Export
@app.route("/admin/export")
@login_required
def export_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Bookings"
    headers = ["ID","Type","Test/Items","Price(s)","Total","Name","Phone","Email","Payment","Status","Location"]
    ws.append(headers)
    for b in Booking.query.order_by(Booking.id).all():
        if b.items_json:
            try:
                items = json.loads(b.items_json) if isinstance(b.items_json, str) else b.items_json
                test_items = ", ".join([i.get("title","") for i in items]) if isinstance(items,list) else str(b.items_json)
                prices = ", ".join([str(i.get("price","")) for i in items]) if isinstance(items,list) else ""
            except Exception:
                test_items = b.items_json
                prices = ""
        else:
            test_items = b.test_name or ""
            prices = ""
        ws.append([b.id,b.booking_type,test_items,prices,b.total_amount,b.customer_name,b.phone,b.email,b.payment_mode,b.status,b.location or ""])
    path = os.path.join("exports","bookings.xlsx")
    os.makedirs("exports", exist_ok=True)
    wb.save(path)
    return send_file(path, as_attachment=True)

# API book
@app.route("/api/book", methods=["POST"])
def api_book():
    data = request.json or {}
    booking_type = data.get("type","manual")
    selected_test = data.get("selected_test") or data.get("test_name") or "N/A"
    payment_mode = data.get("payment_mode") or "cash"
    status = "Payment Pending Verification" if booking_type=="checkout" and payment_mode=="upi" else "Pending"
    booking = Booking(
        booking_type=booking_type,
        test_name=selected_test,
        items_json=json.dumps(data.get("items")) if data.get("items") else None,
        total_amount=data.get("total_amount"),
        customer_name=data.get("name"),
        phone=data.get("phone"),
        email=data.get("email") or "",
        message=data.get("message") or "",
        address=data.get("address"),
        location=data.get("location"),
        preferred_date=data.get("preferred_date"),
        preferred_time=data.get("preferred_time"),
        payment_mode=payment_mode,
        status=status
    )
    db.session.add(booking)
    db.session.commit()
    print(f"📌 New booking saved (ID={booking.id}, Type={booking_type}, Payment={payment_mode})")
    return jsonify({"success": True, "id": booking.id})

# WhatsApp Webhook
@app.route("/webhook", methods=["GET","POST"])
def whatsapp_webhook():
    if request.method=="GET":
        mode=request.args.get("hub.mode")
        token=request.args.get("hub.verify_token")
        challenge=request.args.get("hub.challenge")
        if mode=="subscribe" and token==WHATSAPP_VERIFY_TOKEN:
            return challenge,200
        return "Verification failed",403
    raw_body=request.get_data()
    signature=request.headers.get("X-Hub-Signature-256")
    if WHATSAPP_APP_SECRET and signature:
        expected="sha256="+hmac.new(WHATSAPP_APP_SECRET.encode("utf-8"),raw_body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature):
            return "Invalid signature",403
    payload=request.get_json()
    print("WHATSAPP WEBHOOK PAYLOAD:",json.dumps(payload)[:2000])
    try:
        entries=payload.get("entry",[])
        for entry in entries:
            for change in entry.get("changes",[]):
                val=change.get("value",{})
                messages=val.get("messages",[]) or []
                for m in messages:
                    from_num=m.get("from")
                    text=m.get("text",{}).get("body")
                    print(f"Incoming message from {from_num}: {text}")
    except Exception as e:
        print("Webhook parsing error:",e)
    return "EVENT_RECEIVED",200

# Test WhatsApp route
@app.route("/test-whatsapp")
def test_whatsapp():
    test_number = request.args.get("to") or TEST_PHONE_NUMBER
    if not test_number:
        return jsonify({"error":"No test number set. Add WHATSAPP_TEST_NUMBER in .env or pass ?to=9198XXXXX"}),400
    resp = send_whatsapp(test_number, "Hello! This is a test from Smart Health Lab backend.")
    return jsonify({"result":resp})

# Send test WhatsApp (missing previously)
@app.route("/send-test-whatsapp")
def send_test_whatsapp():
    if not TEST_PHONE_NUMBER:
        return "No test number configured in .env", 400
    resp = send_whatsapp(TEST_PHONE_NUMBER, "This is a test WhatsApp from Smart Health Lab.")
    return jsonify({"result": resp})

import threading, time

def keep_alive():
    """Periodically pings the backend every 10 minutes."""
    while True:
        try:
            requests.get("http://127.0.0.1:5000")  # or your deployed URL
            print("[KEEP-ALIVE] Ping sent to backend ✅")
        except Exception as e:
            print(f"[KEEP-ALIVE] Error: {e}")
        time.sleep(600)  # 600 seconds = 10 minutes

# Start background thread
threading.Thread(target=keep_alive, daemon=True).start()


# ---------------- Run ----------------
if __name__=="__main__":
    with app.app_context():
        db.create_all()
        if ADMIN_EMAIL and ADMIN_PASSWORD and not Admin.query.filter_by(email=ADMIN_EMAIL).first():
            db.session.add(Admin(email=ADMIN_EMAIL,password_hash=generate_password_hash(ADMIN_PASSWORD)))
            db.session.commit()
            print(f"[INIT] Admin created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

