"""
Initializes the database schema and populates it with sample data covering
all three roles, so the app can be explored immediately after setup.

Usage:
    python seed.py            # create tables + seed (skips if data exists)
    python seed.py --reset    # drop all tables, recreate, and reseed
"""
import sys

from app import create_app
from app.extensions import db
from app.models import User, Role, Consultation, ClinicalNote, ConsultationStatus


def seed():
    app = create_app()
    with app.app_context():
        if "--reset" in sys.argv:
            print("Dropping all tables...")
            db.drop_all()

        db.create_all()

        if User.query.first() is not None:
            print("Database already contains data -- skipping seed. Use --reset to start fresh.")
            return

        print("Seeding sample users...")

        admin = User(
            username="admin",
            email="admin@acc-consultation.local",
            full_name="Alex Morgan",
            role=Role.SUPER_ADMIN.value,
        )
        admin.set_password("Admin@12345")

        dr_santos = User(
            username="dr.santos",
            email="santos@acc-consultation.local",
            full_name="Dr. Elena Santos",
            role=Role.MEDICAL_EXPERT.value,
        )
        dr_santos.set_password("Expert@12345")

        dr_cruz = User(
            username="dr.cruz",
            email="cruz@acc-consultation.local",
            full_name="Dr. Marco Cruz",
            role=Role.MEDICAL_EXPERT.value,
        )
        dr_cruz.set_password("Expert@12345")

        student_reyes = User(
            username="student.reyes",
            email="reyes@acc-consultation.local",
            full_name="Jamie Reyes",
            role=Role.STUDENT.value,
        )
        student_reyes.set_password("Student@12345")

        student_tan = User(
            username="student.tan",
            email="tan@acc-consultation.local",
            full_name="Priya Tan",
            role=Role.STUDENT.value,
        )
        student_tan.set_password("Student@12345")

        db.session.add_all([admin, dr_santos, dr_cruz, student_reyes, student_tan])
        db.session.commit()

        print("Seeding sample consultations...")

        c1 = Consultation(
            title="Recurrent Migraines - Follow Up",
            patient_name="Maria Lopez",
            patient_age=34,
            patient_gender="Female",
            description="Patient reports recurring migraines over the past 3 months, "
            "occurring 2-3 times per week, often accompanied by light sensitivity.",
            diagnosis="Suspected chronic migraine without aura; MRI ruled out structural causes.",
            status=ConsultationStatus.IN_PROGRESS.value,
            expert_id=dr_santos.id,
            created_by_id=admin.id,
        )
        c1.observing_students = [student_reyes, student_tan]

        c2 = Consultation(
            title="Type 2 Diabetes - Initial Assessment",
            patient_name="Robert Kim",
            patient_age=52,
            patient_gender="Male",
            description="New patient presenting with elevated fasting glucose and family "
            "history of type 2 diabetes. Referred for full metabolic workup.",
            diagnosis="",
            status=ConsultationStatus.OPEN.value,
            expert_id=dr_santos.id,
            created_by_id=admin.id,
        )
        c2.observing_students = [student_reyes]

        c3 = Consultation(
            title="Post-Op Recovery - Knee Arthroscopy",
            patient_name="Grace Villanueva",
            patient_age=41,
            patient_gender="Female",
            description="Six-week post-operative review following left knee arthroscopy. "
            "Assessing range of motion and pain management plan.",
            diagnosis="Recovery progressing within expected range; mild residual swelling.",
            status=ConsultationStatus.CLOSED.value,
            expert_id=dr_cruz.id,
            created_by_id=admin.id,
        )
        c3.observing_students = [student_tan]

        c4 = Consultation(
            title="Pediatric Asthma Evaluation",
            patient_name="Noah Bennett",
            patient_age=9,
            patient_gender="Male",
            description="Parents report increased frequency of wheezing episodes during "
            "physical activity. Evaluating for exercise-induced asthma.",
            diagnosis="",
            status=ConsultationStatus.OPEN.value,
            expert_id=None,
            created_by_id=admin.id,
        )

        db.session.add_all([c1, c2, c3, c4])
        db.session.commit()

        notes = [
            ClinicalNote(
                consultation_id=c1.id,
                author_id=dr_santos.id,
                note_type="note",
                content="Started patient on a trial of propranolol for prophylaxis. Advised migraine diary.",
            ),
            ClinicalNote(
                consultation_id=c1.id,
                author_id=dr_santos.id,
                note_type="diagnosis",
                content="Chronic migraine without aura (ICHD-3 criteria met). No red-flag features on exam.",
            ),
            ClinicalNote(
                consultation_id=c3.id,
                author_id=dr_cruz.id,
                note_type="note",
                content="Range of motion at 110 degrees flexion, improving steadily. Continue physiotherapy.",
            ),
        ]
        db.session.add_all(notes)
        db.session.commit()

        print("\nSeed complete. Sample login credentials:")
        print("  Super Admin     -> username: admin            password: Admin@12345")
        print("  Medical Expert  -> username: dr.santos         password: Expert@12345")
        print("  Medical Expert  -> username: dr.cruz            password: Expert@12345")
        print("  Student         -> username: student.reyes     password: Student@12345")
        print("  Student         -> username: student.tan       password: Student@12345")
        print("\nIMPORTANT: change these passwords before any real/production deployment.")


if __name__ == "__main__":
    seed()
