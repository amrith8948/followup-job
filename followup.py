import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (important for local testing)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

WATI_API_KEY = os.getenv("WATI_API_KEY")
WATI_BASE_URL = os.getenv("WATI_BASE_URL")

TABLE_NAME = "admissions_chat"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase credentials missing")

if not WATI_API_KEY or not WATI_BASE_URL:
    raise Exception("WATI credentials missing")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# 24 hours ago timestamp
cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()

print("Checking for inactive leads before:", cutoff_time)

try:
    # Fetch leads that:
    # - last_interaction < 24 hours ago
    # - followup_sent = false
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
        f"?last_interaction=lt.{cutoff_time}"
        f"&followup_sent=eq.false",
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Supabase error: {response.text}")

    leads = response.json()

    print(f"Found {len(leads)} leads for followup.")

    for lead in leads:
        phone = lead["phone_number"]
        lead_type = lead.get("lead_type", "Warm")

        # Personalized follow-up message
        if lead_type == "Hot":
            message = "Hi 😊 Just checking — would you like to proceed with ACCA/CMA admission process?"
        else:
            message = "Hi 😊 Just checking if you need more details about ACCA or CMA courses."

        print(f"Sending followup to {phone}")

        # Send WhatsApp message via WATI
        send_response = requests.post(
            f"{WATI_BASE_URL}/api/v1/sendSessionMessage/{phone}",
            headers={
                "Authorization": f"Bearer {WATI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"messageText": message},
            timeout=10
        )

        if send_response.status_code != 200:
            print(f"Failed sending to {phone}: {send_response.text}")
            continue

        # Mark followup_sent = true
        update_response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
            f"?phone_number=eq.{phone}",
            headers=headers,
            json={
                "followup_sent": True,
                "updated_at": datetime.utcnow().isoformat()
            },
            timeout=10
        )

        if update_response.status_code == 204:
            print(f"Followup marked for {phone}")
        else:
            print(f"Failed updating {phone}: {update_response.text}")

except Exception as e:
    print("ERROR:", str(e))

print("Followup job completed.")
