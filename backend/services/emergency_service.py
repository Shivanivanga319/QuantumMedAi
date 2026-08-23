from schemas.emergency_schema import EmergencyRequest


def emergency_response(data: EmergencyRequest):

    # ---------------------------------------
    # 1. Cardiac Arrest / Heart Attack
    # ---------------------------------------

    if data.chest_pain and not data.breathing:

        return {
            "emergency": "Possible Heart Attack / Cardiac Arrest",
            "severity": "Critical",
            "confidence": "96%",
            "doctor": "Cardiologist / Emergency Physician",

            "first_aid": [
                "Call emergency medical services immediately.",
                "Check if the patient responds.",
                "If the patient is not breathing normally, begin CPR immediately if trained.",
                "Use an AED (Automated External Defibrillator) if available.",
                "Loosen tight clothing.",
                "Do NOT give food or water.",
                "Continue monitoring until medical professionals arrive."
            ]
        }

    # ---------------------------------------
    # 2. Brain Stroke
    # ---------------------------------------

    if data.speech_problem and data.paralysis:

        return {
            "emergency": "Possible Brain Stroke",
            "severity": "Critical",
            "confidence": "95%",
            "doctor": "Neurologist",

            "first_aid": [
                "Call emergency medical services immediately.",
                "Note the exact time symptoms started.",
                "Lay the patient comfortably with the head slightly elevated.",
                "Do NOT give food, water, or medicine.",
                "Monitor breathing until help arrives."
            ]
        }

    # ---------------------------------------
    # 3. Choking
    # ---------------------------------------

    if data.choking:

        return {

            "emergency": "Possible Airway Obstruction (Choking)",

            "severity": "Critical",

            "confidence": "94%",

            "doctor": "Emergency Physician",

            "first_aid": [

                "Ask if the person can cough or speak.",
                "If unable to breathe or speak, give 5 back blows.",
                "If unsuccessful, perform abdominal thrusts (Heimlich maneuver) for adults if trained.",
                "Call emergency medical services immediately.",
                "If the person becomes unconscious, begin CPR if trained."

            ]
        }

    # ---------------------------------------
    # 4. Severe Bleeding
    # ---------------------------------------

    if data.severe_bleeding:

        return {

            "emergency": "Severe Bleeding",

            "severity": "Critical",

            "confidence": "95%",

            "doctor": "Trauma Surgeon / Emergency Physician",

            "first_aid": [

                "Apply firm pressure directly on the wound using a clean cloth or bandage.",
                "Keep the injured area elevated if possible.",
                "Do not remove objects embedded in the wound.",
                "Call emergency medical services immediately."

            ]
        }

    # ---------------------------------------
    # 5. Seizure
    # ---------------------------------------

    if data.seizure:

        return {

            "emergency": "Seizure Emergency",

            "severity": "High",

            "confidence": "92%",

            "doctor": "Neurologist",

            "first_aid": [

                "Keep the patient away from dangerous objects.",
                "Do NOT hold the patient down.",
                "Do NOT place anything in the mouth.",
                "Turn the patient onto one side after the seizure stops.",
                "Call emergency services if the seizure lasts more than 5 minutes."

            ]
        }

    # ---------------------------------------
    # 6. Possible Kidney Infection
    # ---------------------------------------

    if data.fever and data.vomiting:

        return {

            "emergency": "Possible Kidney Infection",

            "severity": "Moderate",

            "confidence": "88%",

            "doctor": "Nephrologist",

            "first_aid": [

                "Drink water if the patient is conscious and not vomiting continuously.",
                "Monitor body temperature.",
                "Seek medical evaluation as soon as possible."

            ]
        }

    # ---------------------------------------
    # 7. Food Poisoning
    # ---------------------------------------

    if data.abdominal_pain and data.vomiting:

        return {

            "emergency": "Possible Food Poisoning",

            "severity": "Moderate",

            "confidence": "87%",

            "doctor": "General Physician",

            "first_aid": [

                "Drink oral rehydration solution in small sips if tolerated.",
                "Avoid oily and spicy foods.",
                "Seek medical care if symptoms become severe or persist."

            ]
        }

    # ---------------------------------------
    # 8. Unconscious
    # ---------------------------------------

    if not data.conscious:

        return {

            "emergency": "Patient Unconscious",

            "severity": "Critical",

            "confidence": "94%",

            "doctor": "Emergency Physician",

            "first_aid": [

                "Call emergency medical services immediately.",
                "Check breathing and pulse.",
                "If not breathing normally, begin CPR if trained.",
                "Place the patient in the recovery position if breathing normally.",
                "Continue monitoring until help arrives."

            ]
        }

    # ---------------------------------------
    # 9. Normal
    # ---------------------------------------

    return {

        "emergency": "No Critical Emergency",

        "severity": "Low",

        "confidence": "98%",

        "doctor": "General Physician",

        "first_aid": [

            "Monitor the symptoms carefully.",
            "Encourage rest and hydration.",
            "Visit the nearest hospital if symptoms worsen."

        ]
    }