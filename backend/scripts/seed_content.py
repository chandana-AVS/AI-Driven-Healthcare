"""Seed sample healthcare education content.

All items are inserted as DRAFT. They are general public-health messages, but an administrator must have
them reviewed by a qualified healthcare professional before publishing — they are not clinical advice.

Usage (from backend/):  python -m scripts.seed_content
"""
from app.database import SessionLocal
from app.models import HealthcareContent, User
from app.models.enums import UserRole

SAMPLES = [
    ("GENERAL_HEALTH", "Washing Hands Properly",
     "Wash hands with soap and clean water for at least 20 seconds, especially before eating or cooking, "
     "after using the toilet, and after caring for someone who is sick. Clean hands help prevent many "
     "common infections."),
    ("MATERNAL_HEALTH", "Regular Check-ups During Pregnancy",
     "Pregnant women should register at the nearest health centre early and attend all scheduled antenatal "
     "check-ups. Inform a health worker promptly about bleeding, severe headache, swelling, fever or reduced "
     "baby movements."),
    ("CHILD_HEALTHCARE", "Keeping Your Child's Vaccinations on Schedule",
     "Vaccines protect children from serious diseases. Keep the vaccination card safe, and visit the health "
     "centre on each due date. Ask your health worker if a dose was missed."),
    ("ELDERLY_CARE", "Preventing Falls at Home",
     "Keep floors dry and free of clutter, add lighting near steps and the toilet, and use support rails or "
     "walking aids where needed. Regular eyesight checks also reduce the risk of falls."),
    ("PREVENTIVE_HEALTHCARE", "Safe Drinking Water",
     "Drink water from a safe source. If unsure, boil water and let it cool, and store it in a clean covered "
     "container. Safe water helps prevent diarrhoea and other water-borne illnesses."),
    ("COMMON_DISEASES", "Recognising Dehydration from Diarrhoea",
     "Signs of dehydration include extreme thirst, very little urine, dry mouth and unusual tiredness. Give "
     "oral rehydration solution (ORS) as directed and seek care quickly for infants, the elderly, or if signs "
     "worsen."),
]


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
        created = 0
        for category, title, body in SAMPLES:
            if db.query(HealthcareContent).filter(HealthcareContent.title == title).first():
                continue
            db.add(HealthcareContent(
                title=title, body=body, category=category, language_code="en", status="DRAFT",
                created_by=admin.id if admin else None,
            ))
            created += 1
        db.commit()
        print(f"Seeded {created} content item(s) as DRAFT. Review them, then publish from the admin dashboard.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
