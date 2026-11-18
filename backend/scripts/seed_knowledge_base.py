"""Seed the multilingual knowledge base (Milestone 2): healthcare FAQs and common-disease information in English.

Usage (from backend/):
    python -m scripts.seed_knowledge_base                       # insert as DRAFT (review, then publish in the admin panel)
    python -m scripts.seed_knowledge_base --publish             # insert as PUBLISHED
    python -m scripts.seed_knowledge_base --publish --translate te hi ta kn ml
                                                                # also create AI translations (needs OPENAI_API_KEY)
Entries whose English title already exists are skipped, so the script is safe to run again.
The text is general awareness information; have it reviewed by a qualified health professional before real use.
"""
import argparse
import sys

from app.database import SessionLocal
from app.models import HealthcareContent, User
from app.models.enums import ContentStatus, ContentType, UserRole

FAQS = [
    ("How do I make ORS (oral rehydration solution) at home?", "GENERAL_HEALTH",
     "If you do not have an ORS packet, mix 6 level teaspoons of sugar and half a level teaspoon of salt in 1 litre "
     "of clean, boiled and cooled drinking water. Stir until dissolved.\n\n"
     "Give small sips often. For a child with loose motions, give ORS after every loose stool. Make a fresh solution "
     "every day. ORS packets from the health centre or pharmacy are better when available.\n\n"
     "See a doctor quickly if the person cannot drink, is very sleepy, has blood in the stool or has not passed urine for many hours."),
    ("What do OD, BD, TDS and SOS mean on my prescription?", "GENERAL_HEALTH",
     "Doctors often write short forms on prescriptions:\n"
     "- OD: once a day\n- BD: twice a day\n- TDS: three times a day\n- QID: four times a day\n"
     "- HS: at bedtime\n- AC: before food\n- PC: after food\n- SOS: only when needed\n\n"
     "If you are not sure how to take a medicine, ask the doctor, nurse or pharmacist before you start. "
     "Do not stop a medicine early just because you feel better unless the doctor tells you to."),
    ("When should I call 108 or go to the hospital immediately?", "GENERAL_HEALTH",
     "Call 108 for an ambulance or go to the nearest hospital at once if someone has:\n"
     "- chest pain or difficulty breathing\n- fainting, fits (seizures) or is very confused\n"
     "- sudden weakness of the face, arm or leg, or trouble speaking\n- heavy bleeding or a serious injury\n"
     "- a snake bite, poisoning or a severe burn\n"
     "- in pregnancy: bleeding, severe headache, fits, severe belly pain or the baby moving much less\n"
     "- a baby with fever who is not feeding or is very sleepy"),
    ("When does a fever need a doctor?", "GENERAL_HEALTH",
     "Most fevers get better in a few days with rest and fluids. See a doctor if the fever lasts more than 2 to 3 days, "
     "is very high, comes with chills and shivering, rash, severe headache, stiff neck, vomiting, breathing difficulty "
     "or bleeding from the gums or nose.\n\n"
     "In areas with dengue or malaria, a fever should be tested at the health centre. Babies under 3 months with any "
     "fever should be seen by a doctor the same day."),
    ("Why and how should I wash my hands?", "PREVENTIVE_HEALTHCARE",
     "Washing hands with soap and water stops many infections, including diarrhoea and colds.\n\n"
     "Wash before cooking, before eating, before feeding a child, and after using the toilet, cleaning a child or "
     "touching animals. Rub all parts of the hands with soap for about 20 seconds, then rinse with clean water."),
    ("How can I keep drinking water safe?", "PREVENTIVE_HEALTHCARE",
     "Unsafe water spreads diarrhoea, typhoid, cholera and jaundice. Boil water for at least one minute and let it cool "
     "in a covered vessel, or use a water filter or chlorine tablets as advised by the health worker.\n\n"
     "Store water in a clean, covered container and take it out with a long-handled cup, not with your hands."),
    ("Which vaccines does my child need?", "CHILD_HEALTHCARE",
     "Under the Universal Immunisation Programme, children receive free vaccines at government health centres and "
     "Anganwadi sessions from birth through childhood. They protect against diseases such as tuberculosis, polio, "
     "measles, diphtheria, whooping cough, tetanus and hepatitis B.\n\n"
     "Keep the Mother and Child Protection card safe and bring it to every visit. The ASHA worker or ANM can tell you "
     "the next due date. If a dose was missed, it can usually still be given, so ask at the health centre."),
]

DISEASES = [
    ("Dengue", "COMMON_DISEASES",
     "Dengue is a viral infection spread by the bite of Aedes mosquitoes, which bite during the day.\n\n"
     "Common signs: sudden high fever, severe headache, pain behind the eyes, body and joint pain, and sometimes a rash.\n\n"
     "Danger signs (go to hospital at once): severe belly pain, repeated vomiting, bleeding from gums or nose, black stools, "
     "extreme tiredness or restlessness, cold and clammy skin.\n\n"
     "What to do: get tested at the health centre, rest and drink plenty of fluids. Do not take aspirin or painkillers "
     "like ibuprofen unless a doctor says so.\n\n"
     "Prevention: empty and clean water containers every week, cover water tanks, and use mosquito nets and full sleeves."),
    ("Malaria", "COMMON_DISEASES",
     "Malaria is caused by a parasite spread by the bite of Anopheles mosquitoes, mostly at night.\n\n"
     "Common signs: fever that comes with chills and shivering, sweating, headache, body pain and vomiting.\n\n"
     "What to do: get a blood test (rapid test) at the health centre or from the ASHA worker. Take the full course of "
     "medicine exactly as given, even if you feel better.\n\n"
     "Danger signs: confusion, fits, yellow eyes, very little urine or difficulty breathing need hospital care at once.\n\n"
     "Prevention: sleep under a mosquito net and remove stagnant water near the house."),
    ("Typhoid", "COMMON_DISEASES",
     "Typhoid is a bacterial infection spread through contaminated food and water.\n\n"
     "Common signs: fever that rises over several days, weakness, stomach pain, headache, and constipation or loose motions.\n\n"
     "What to do: see a doctor for testing and treatment. Complete the full course of medicine. Drink plenty of safe fluids.\n\n"
     "Prevention: drink boiled or treated water, wash hands with soap, and eat freshly cooked food."),
    ("Tuberculosis (TB)", "COMMON_DISEASES",
     "TB is a bacterial infection that usually affects the lungs and spreads through the air when a person with TB coughs.\n\n"
     "Common signs: cough for more than 2 weeks, fever especially in the evening, night sweats, weight loss, and sometimes blood in the sputum.\n\n"
     "What to do: get tested at a government health centre, where testing and treatment are free. TB can be cured if "
     "the full course of medicine is taken every day for the whole period. Stopping early can make TB harder to treat.\n\n"
     "Prevention: cover your mouth when coughing, keep rooms airy, and make sure babies get the BCG vaccine."),
    ("Diabetes (high blood sugar)", "COMMON_DISEASES",
     "Diabetes means the sugar level in the blood stays too high. It is long-term and needs regular care.\n\n"
     "Common signs: feeling very thirsty, passing urine often, tiredness, weight loss, slow-healing wounds and blurred vision. "
     "Many people have no signs, so a blood test is important after age 30.\n\n"
     "Living with diabetes: take medicines exactly as prescribed, eat less sugar and fried food, eat more vegetables, "
     "walk daily, check sugar regularly and look after your feet.\n\n"
     "Danger signs: fainting, confusion or heavy sweating with shaking can mean very low sugar and need help at once."),
    ("High blood pressure (hypertension)", "COMMON_DISEASES",
     "High blood pressure means the force of blood in the blood vessels stays too high. It often has no signs, so get "
     "your blood pressure checked regularly after age 30.\n\n"
     "Why it matters: untreated high blood pressure can cause stroke, heart attack and kidney damage.\n\n"
     "What helps: take medicines every day as prescribed, even when you feel well. Eat less salt, pickles and papad, "
     "avoid tobacco and alcohol, stay active and keep a healthy weight.\n\n"
     "Danger signs: severe headache, chest pain, sudden weakness on one side or trouble speaking need emergency care."),
    ("Anaemia (low blood)", "COMMON_DISEASES",
     "Anaemia means there is not enough haemoglobin in the blood. It is common in women, pregnant women and children.\n\n"
     "Common signs: tiredness, weakness, breathlessness on walking, pale eyelids, nails or palms, and dizziness.\n\n"
     "What helps: eat iron-rich foods such as green leafy vegetables, jaggery, pulses, eggs and meat, with lemon or "
     "amla to help absorption. Pregnant women and adolescents can get free iron and folic acid tablets at the health "
     "centre. Treat worms as advised by the health worker."),
    ("Diarrhoea", "COMMON_DISEASES",
     "Diarrhoea is passing loose or watery stools three or more times a day. It is usually caused by germs in unsafe water or food.\n\n"
     "What to do: give ORS and other fluids after every loose stool, keep feeding (continue breastfeeding for babies), "
     "and ask the health worker about zinc tablets for children.\n\n"
     "Danger signs: blood in the stool, very sunken eyes, unable to drink, very sleepy, or no urine for many hours. Go to a doctor at once.\n\n"
     "Prevention: safe drinking water, handwashing with soap and using a toilet."),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed healthcare FAQs and disease information")
    parser.add_argument("--publish", action="store_true", help="insert as PUBLISHED instead of DRAFT")
    parser.add_argument("--translate", nargs="*", metavar="LANG", help="also create AI translations (te hi ta kn ml)")
    args = parser.parse_args()
    status = ContentStatus.PUBLISHED.value if args.publish else ContentStatus.DRAFT.value

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == UserRole.ADMIN.value, User.is_verified.is_(True)).first()
        created = []
        for ctype, rows in ((ContentType.FAQ, FAQS), (ContentType.DISEASE_INFO, DISEASES)):
            for title, category, body in rows:
                if db.query(HealthcareContent).filter(HealthcareContent.title == title,
                                                      HealthcareContent.language_code == "en").first():
                    continue
                item = HealthcareContent(title=title, body=body, category=category, content_type=ctype.value,
                                         language_code="en", status=status, created_by=admin.id if admin else None)
                db.add(item)
                created.append(item)
        db.commit()
        print(f"Inserted {len(created)} English items as {status} (existing titles skipped).")

        if args.translate:
            if admin is None:
                sys.exit("Error: translations need a verified admin account (scripts.create_admin).")
            from fastapi import HTTPException

            from app.services import knowledge_service
            langs = [lang for lang in args.translate if lang != "en"]
            targets = db.query(HealthcareContent).filter(
                HealthcareContent.language_code == "en",
                HealthcareContent.content_type.in_([ContentType.FAQ.value, ContentType.DISEASE_INFO.value])).all()
            for item in targets:
                try:
                    copies = knowledge_service.translate_item(db, item, langs, admin)
                except HTTPException as exc:
                    print(f"  skip '{item.title}': {exc.detail}")
                    continue
                for c in copies:
                    c.status = status
                db.commit()
                print(f"  translated '{item.title}' -> {', '.join(c.language_code for c in copies)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
