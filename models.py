# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    dob = db.Column(db.Date)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional file attachment relationship (if added later)
    attachments = db.relationship("Attachment", backref="patient", lazy=True)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)

