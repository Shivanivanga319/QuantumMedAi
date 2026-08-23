import os
import urllib.parse
from typing import Dict, Any, Optional

def format_emergency_sms_payload(
    patient_name: str,
    emergency_type: str,
    severity: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    first_aid_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs an offline/low-bandwidth emergency SMS and WhatsApp message payload
    with live GPS coordinates and clickable Google Maps link.
    """
    clean_name = patient_name or "Unknown Patient"
    clean_type = emergency_type or "Acute Medical Emergency"
    clean_sev = severity or "Critical"

    maps_link = ""
    coords_text = "Coordinates: Unavailable"
    if lat is not None and lng is not None:
        maps_link = f"https://maps.google.com/?q={lat},{lng}"
        coords_text = f"GPS: {lat:.5f}, {lng:.5f}\nLive Location: {maps_link}"

    # Construct the ultra-clear SMS Dispatch Text
    sms_text = (
        f"🚨 [QUANTUMMED AI EMERGENCY ALERT]\n"
        f"Patient: {clean_name}\n"
        f"Status: {clean_sev.upper()} - {clean_type}\n"
        f"{coords_text}\n"
        f"Need immediate ambulance / medical dispatch. Call 108 immediately."
    )

    if first_aid_summary:
        sms_text += f"\nFirst-Aid: {first_aid_summary}"

    # URL-encoded strings for direct hardware protocols
    sms_encoded = urllib.parse.quote(sms_text)
    whatsapp_encoded = urllib.parse.quote(sms_text)

    return {
        "status": "success",
        "raw_text": sms_text,
        "patient_name": clean_name,
        "emergency_type": clean_type,
        "severity": clean_sev,
        "lat": lat,
        "lng": lng,
        "maps_link": maps_link,
        # Direct hardware protocol URLs for 100% offline device triggering
        "sms_uri": f"sms:108?body={sms_encoded}",
        "whatsapp_url": f"https://wa.me/?text={whatsapp_encoded}"
    }


def dispatch_sms_via_cloud(payload: Dict[str, Any], destination_number: str = "108") -> Dict[str, Any]:
    """
    Sends the SMS through Twilio or Exotel if API credentials are configured in .env,
    otherwise returns the direct hardware protocol payload.
    """
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER")

    if twilio_sid and twilio_token and twilio_from:
        try:
            # Twilio integration if credentials exist
            import httpx
            auth = (twilio_sid, twilio_token)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            data = {
                "From": twilio_from,
                "To": destination_number,
                "Body": payload.get("raw_text", "EMERGENCY MEDICAL ALERT")
            }
            with httpx.Client(timeout=3.0) as client:
                res = client.post(url, data=data, auth=auth)
                if res.status_code in [200, 201]:
                    return {
                        "delivered": True,
                        "provider": "Twilio Cloud Gateway",
                        "message_id": res.json().get("sid"),
                        **payload
                    }
        except Exception as e:
            print(f"[Twilio Gateway Dispatch Error]: {e}")

    # Default fallback to direct client-side cellular / SMS protocol
    return {
        "delivered": False,
        "provider": "Native Cellular SMS & WhatsApp Fallback",
        "instructions": "Triggered via direct mobile intent protocol",
        **payload
    }
