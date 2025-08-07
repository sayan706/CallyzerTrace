from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta, time
import time as t
import json

app = Flask(__name__)

API_TOKEN = "give your token"
API_URL = "https://api1.callyzer.co/api/v2.1/call-log/history"

def get_ist_epoch(hour, minute, target_date=None):
    """Return UTC epoch timestamp in seconds after setting IST time."""
    if target_date:
        ist_today = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        now_utc = datetime.utcnow()
        ist_now = now_utc + timedelta(hours=5, minutes=30)
        ist_today = ist_now.date()

    ist_datetime = datetime.combine(ist_today, time(hour, minute))
    corrected_utc = ist_datetime - timedelta(hours=5, minutes=30)
    return int(corrected_utc.timestamp())
@app.route('/filter-client', methods=['POST'])
def filter_client():
    try:
        data = request.get_json(force=True)
        emp_number = data.get("emp_number")
        target_client_number = data.get("target_client_number")
        custom_date = data.get("custom_date")  # optional field, format: 'YYYY-MM-DD'

        if not emp_number or not target_client_number:
            return jsonify({"error": "Missing emp_number or target_client_number"}), 400

        # Get epoch times for start and end of the given day (IST)
        call_from = get_ist_epoch(0, 0, custom_date)
        call_to = get_ist_epoch(23, 59, custom_date)

        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "call_from": call_from,
            "call_to": call_to,
            "emp_numbers": [emp_number],
            "call_types": ["Outgoing", "Incoming"],
            "page_no": 1,
            "page_size": 100
        }

        max_retries = 3
        backoff_delay = 5

        for attempt in range(1, max_retries + 1):
            response = requests.post(API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                api_data = response.json()
                filtered_clients = [
                    item for item in api_data.get("result", [])
                    if item.get("client_number") == target_client_number
                ]
                return jsonify({
                    "filtered_results": filtered_clients,
                    "count": len(filtered_clients)
                })
            elif response.status_code == 429:
                t.sleep(backoff_delay)
                backoff_delay *= 2
            else:
                return jsonify({"error": f"{response.status_code}: {response.text}"}), response.status_code

        return jsonify({"error": "All retries failed. Try again later."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
