"""Initial create with pt_notes including soft delete columns

Revision ID: initial_create_with_pt_notes
Revises: 
Create Date: 2025-07-04 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = 'initial_create_with_pt_notes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create insurances table
    op.create_table(
        'insurances',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_name', sa.String(128), nullable=False),
        sa.Column('plan_name', sa.String(128)),
        sa.Column('phone', sa.String(20)),
    )

    # Create physicians table
    op.create_table(
        'physicians',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('first_name', sa.String(64), nullable=False),
        sa.Column('last_name', sa.String(64), nullable=False),
        sa.Column('specialty', sa.String(128)),
        sa.Column('email', sa.String(120), unique=True),
        sa.Column('phone', sa.String(20)),
    )

    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('first_name', sa.String(64), nullable=False),
        sa.Column('last_name', sa.String(64), nullable=False),
        sa.Column('dob', sa.Date),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(120)),
        sa.Column('address', sa.String(256)),
        sa.Column('insurance_id', sa.Integer, sa.ForeignKey('insurances.id')),
        sa.Column('physician_id', sa.Integer, sa.ForeignKey('physicians.id')),
    )

    # Create therapists table
    op.create_table(
        'therapists',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(150), unique=True, nullable=False),
        sa.Column('password', sa.String(200), nullable=False),
        sa.Column('first_name', sa.String(64), nullable=False),
        sa.Column('last_name', sa.String(64), nullable=False),
        sa.Column('credentials', sa.String(128)),
        sa.Column('email', sa.String(120), unique=True),
        sa.Column('phone', sa.String(20)),
        sa.Column('availability', sa.String(256)),
    )

    # Create cpt_codes table
    op.create_table(
        'cpt_codes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.String(10), unique=True, nullable=False),
        sa.Column('description', sa.String(256)),
    )

    # Create icd10_codes table
    op.create_table(
        'icd10_codes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.String(10), unique=True, nullable=False),
        sa.Column('description', sa.String(256)),
    )

    # Create visits table
    op.create_table(
        'visits',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('patient_id', sa.Integer, sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('therapist_id', sa.Integer, sa.ForeignKey('therapists.id'), nullable=False),
        sa.Column('visit_date', sa.DateTime, default=func.now()),
        sa.Column('end_time', sa.DateTime),
        sa.Column('duration', sa.Integer, default=60),
        sa.Column('visit_type', sa.String(64)),
        sa.Column('status', sa.String(32), default='Scheduled'),
        sa.Column('cpt_code_id', sa.Integer, sa.ForeignKey('cpt_codes.id')),
        sa.Column('icd10_code_id', sa.Integer, sa.ForeignKey('icd10_codes.id')),
        sa.Column('notes', sa.Text),
        sa.Column('google_event_id', sa.String(128)),
    )

    # Create billings table
    op.create_table(
        'billings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('visit_id', sa.Integer, sa.ForeignKey('visits.id'), nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('paid', sa.Boolean, default=False),
        sa.Column('payment_date', sa.DateTime),
        sa.Column('payment_method', sa.String(64)),
        sa.Column('notes', sa.Text),
    )

    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('filename', sa.String(200)),
        sa.Column('filepath', sa.String(300)),
        sa.Column('uploaded_at', sa.DateTime, default=func.now()),
        sa.Column('patient_id', sa.Integer, sa.ForeignKey('patients.id')),
        sa.Column('visit_id', sa.Integer, sa.ForeignKey('visits.id')),
    )

    # Create schedule_event table
    op.create_table(
        'schedule_event',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(128)),
        sa.Column('start', sa.DateTime),
        sa.Column('end', sa.DateTime),
        sa.Column('therapist_id', sa.Integer, sa.ForeignKey('therapists.id')),
        sa.Column('color', sa.String(16), default='#1e90ff'),
    )

    # Create pt_notes table with soft delete columns
    op.create_table(
        'pt_notes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('patient_id', sa.Integer, sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('therapist_id', sa.Integer, sa.ForeignKey('therapists.id')),
        sa.Column('visit_id', sa.Integer, sa.ForeignKey('visits.id')),
        sa.Column('date_created', sa.DateTime, default=func.now()),
        sa.Column('note_type', sa.String(64), default='SOAP'),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('deleted', sa.Boolean, default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
    )


def downgrade():
    op.drop_table('pt_notes')
    op.drop_table('schedule_event')
    op.drop_table('attachments')
    op.drop_table('billings')
    op.drop_table('visits')
    op.drop_table('icd10_codes')
    op.drop_table('cpt_codes')
    op.drop_table('therapists')
    op.drop_table('patients')
    op.drop_table('physicians')
    op.drop_table('insurances')
