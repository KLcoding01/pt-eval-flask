from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association tables for many-to-many if needed later
# e.g. therapist specialties or patient allergies, etc. (not shown here)

class Therapist(db.Model):
    __tablename__ = "therapists"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    credentials = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    availability = db.Column(db.String(256))  # JSON or serialized string for availability schedule
    visits = db.relationship("Visit", back_populates="therapist", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Therapist {self.first_name} {self.last_name}>"


class Physician(db.Model):
    __tablename__ = "physicians"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    specialty = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    patients = db.relationship("Patient", back_populates="physician", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Physician Dr. {self.first_name} {self.last_name}>"


class Insurance(db.Model):
    __tablename__ = "insurances"
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(128), nullable=False)
    plan_name = db.Column(db.String(128))
    phone = db.Column(db.String(20))
    patients = db.relationship("Patient", back_populates="insurance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Insurance {self.company_name}>"


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    dob = db.Column(db.Date)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(256))
    insurance_id = db.Column(db.Integer, db.ForeignKey("insurances.id"), nullable=True)
    physician_id = db.Column(db.Integer, db.ForeignKey("physicians.id"), nullable=True)
    visits = db.relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    insurance = db.relationship("Insurance", back_populates="patients")
    physician = db.relationship("Physician", back_populates="patients")

    def __repr__(self):
        return f"<Patient {self.first_name} {self.last_name}>"


class CPTCode(db.Model):
    __tablename__ = "cpt_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.String(256))

    def __repr__(self):
        return f"<CPT {self.code}>"


class ICD10Code(db.Model):
    __tablename__ = "icd10_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.String(256))

    def __repr__(self):
        return f"<ICD10 {self.code}>"


class Visit(db.Model):
    __tablename__ = "visits"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    therapist_id = db.Column(db.Integer, db.ForeignKey("therapists.id"), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    visit_type = db.Column(db.String(64))  # e.g., Eval, Reassessment, Treatment
    status = db.Column(db.String(32), default="Scheduled")  # Scheduled, Arrived, Cancelled, No Show, Call Confirmed
    cpt_code_id = db.Column(db.Integer, db.ForeignKey("cpt_codes.id"), nullable=True)
    icd10_code_id = db.Column(db.Integer, db.ForeignKey("icd10_codes.id"), nullable=True)
    notes = db.Column(db.Text)
    billing = db.relationship("Billing", uselist=False, back_populates="visit", cascade="all, delete-orphan")
    patient = db.relationship("Patient", back_populates="visits")
    therapist = db.relationship("Therapist", back_populates="visits")
    cpt_code = db.relationship("CPTCode")
    icd10_code = db.relationship("ICD10Code")

    def __repr__(self):
        return f"<Visit {self.visit_type} for {self.patient.first_name} {self.patient.last_name}>"


class Billing(db.Model):
    __tablename__ = "billings"
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime)
    payment_method = db.Column(db.String(64))
    notes = db.Column(db.Text)
    visit = db.relationship("Visit", back_populates="billing")

    def __repr__(self):
        return f"<Billing visit_id={self.visit_id} amount={self.amount} paid={self.paid}>"
        
        
class Attachment(db.Model):
    __tablename__ = "attachments"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    filetype = db.Column(db.String(64))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=True)
    description = db.Column(db.String(256))
    filepath = db.Column(db.String(512), nullable=False)  # path or URL to file

    patient = db.relationship("Patient", backref=db.backref("attachments", lazy="dynamic"))
    visit = db.relationship("Visit", backref=db.backref("attachments", lazy="dynamic"))

    def __repr__(self):
        return f"<Attachment {self.filename}>"
