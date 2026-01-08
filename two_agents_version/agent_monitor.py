import json
import os
import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Using a widely available model on OpenRouter, e.g., meta-llama/llama-3.1-70b-instruct or similar
MODEL_NAME = "meta-llama/llama-3.1-70b-instruct"

# Configuration
INPUT_FILE = "input_events.json"
DB_FILE = "events_db.json"
SUMMARY_JSON = "summary_report.json"
SUMMARY_TXT = "summary_report.txt"

# Resource Counts
RESOURCES = {
    "server": {"count": 10, "day_power": 100, "night_power": 70},
    "workstation": {"count": 20, "day_power": 60, "night_power": 0},
    "automate": {"count": 5, "day_power": 300, "night_power": 0},
    "internet_gateway": {"count": 1, "day_power": 50, "night_power": 50}
}

# CO2 Emission Factor (kg CO2 per kWh) - Estimated global average or specific
CO2_PER_KWH = 0.475

# Event Modifiers
EVENT_MODIFIERS = {
    "cpu_overflow": 1.0,  # +100%
    "cpu_overload": 1.0,  # Synonym
    "cpu_max_heat_threshold": 0.8,
    "fan_failure": 0.5,
    "software_update": -0.3,
    "operating_system_update": -0.3,
    "software_service_failure": -0.7,
    "operating_system_failure": -1.0,
    "hardware_failure": -1.0,
    "hardware_maintenance_stop": -1.0
}

def get_llm_response(prompt, system_prompt="You are a helpful AI assistant."):
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not found. Returning dummy response.")
        return "LLM Analysis Unavailable: API Key missing."
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return f"Error: {str(e)}"

def predict_failures(events_data):
    print("Analyzing events for failure prediction...")
    # Process each resource
    for res_name, res_data in events_data.items():
        events_list = res_data.get("events", [])
        if not events_list:
            res_data["failure_prediction"] = "Low risk (No recent events)"
            continue
        
        prompt = f"Analyze the following events for resource '{res_name}' ({res_data['type']}) and predict the probability of future failures. Events: {json.dumps(events_list)}"
        prediction = get_llm_response(prompt, system_prompt="You are an IT infrastructure expert. Analyze logs to predict failure risks.")
        res_data["failure_prediction"] = prediction
    
    return events_data

def calculate_energy_for_interval(resource_type, start_dt, end_dt, events):
    """
    Calculate energy consumption (Wh) for a single resource instance between start_dt and end_dt,
    considering the provided events.
    """
    total_energy_wh = 0
    
    # We iterate hour by hour for simplicity and accuracy with day/night cycles
    # Or we can integrate. Given the complexity, minute-by-minute or hour-by-hour simulation is safer.
    # Let's do hourly integration.
    
    current_time = start_dt
    while current_time < end_dt:
        next_hour = current_time + datetime.timedelta(hours=1)
        # Cap at end_dt
        if next_hour > end_dt:
            next_hour = end_dt
            
        # Determine duration in hours
        duration_hours = (next_hour - current_time).total_seconds() / 3600.0
        
        # Determine base power
        # Production time: 8 am to 8 pm (08:00 to 20:00)
        hour = current_time.hour
        is_production = 8 <= hour < 20
        
        res_info = RESOURCES.get(resource_type, {})
        if not res_info:
            base_power = 0
        else:
            base_power = res_info["day_power"] if is_production else res_info["night_power"]
            
        # Apply event modifiers
        modifier_sum = 0
        for event in events:
            # Check overlap
            # Event times are strings, need parsing. 
            # Optimization: Parse times once before calling this function.
            # Assuming event objects passed here have datetime objects.
            
            evt_start = event["start_dt"]
            evt_end = event["end_dt"]
            
            # Check if event overlaps with current interval [current_time, next_hour]
            if max(current_time, evt_start) < min(next_hour, evt_end):
                # It overlaps.
                # The prompt implies the modifier applies to the consumption.
                # "for event ..., +X% Watts per hour consumption"
                # We assume if the event is active during this hour, the power is modified.
                # Simplification: If event is active for ANY part of the hour? 
                # Better: Weighted average?
                # Best: Check if event covers the *entire* interval or part.
                # Since we step by hour, let's just check if it overlaps.
                # If we want to be precise, we need to split intervals.
                # For this challenge, let's apply the modifier if the event is active at the START of the interval
                # or split the interval.
                # Let's use a simpler approach: Calculate modifier for the *overlapping duration*.
                
                # Actually, let's keep it simple:
                # Power = Base * (1 + sum(modifiers))
                # This works if modifiers are additive.
                # "-100%" means 0 consumption.
                # If multiple events? We sum the percentages? e.g. +100% and -30% = +70%?
                # Or multiplicative?
                # Prompt says "+100% ... -30%". Implies additive to the base.
                # e.g. Base + (Base * 1.0) - (Base * 0.3).
                
                etype = event.get("event_type", "").lower()
                # Normalize key
                if etype == "cpu_overflow": etype = "cpu_overflow" 
                # ... handle mapping
                
                mod_val = EVENT_MODIFIERS.get(etype, 0)
                modifier_sum += mod_val
        
        # Cap modifier? -100% is the floor usually (cannot have negative consumption).
        # If modifier_sum is -2.0, power is 0.
        effective_modifier = max(-1.0, modifier_sum)
        
        power = base_power * (1 + effective_modifier)
        total_energy_wh += power * duration_hours
        
        current_time = next_hour
        
    return total_energy_wh

def process_energy_calculations(events_data):
    print("Calculating energy consumption...")
    
    # Define "Last Week"
    # Assuming "Last Week" means the last 7 complete days or just last 7 days from now.
    # Let's take the last 7 days ending at 2026-01-08 00:00:00 for consistency with the environment date.
    # Or just "Now" - 7 days.
    # Environment says "Today's date: 2026-01-08".
    end_date = datetime.datetime(2026, 1, 8, 0, 0, 0)
    start_date = end_date - datetime.timedelta(days=7)
    
    print(f"Calculation Period: {start_date} to {end_date}")
    
    summary_data = {
        "period_start": str(start_date),
        "period_end": str(end_date),
        "resources": {},
        "total_energy_wh": 0,
        "total_co2_kg": 0
    }
    
    # We need to process ALL resources, not just those in events_data.
    # The prompt implies we have "10 servers, 20 workstations...".
    # events_data only contains resources WITH events (or mentioned).
    # We should iterate through the theoretical inventory.
    # But we need names. "server_1", "workstation_2".
    # We will assume resources named "server_1" to "server_10", etc.
    
    inventory = []
    for r_type, info in RESOURCES.items():
        for i in range(1, info["count"] + 1):
            inventory.append(f"{r_type}_{i}")
            
    for res_name in inventory:
        # Determine resource type
        if res_name.startswith("server"): r_type = "server"
        elif res_name.startswith("workstation"): r_type = "workstation"
        elif res_name.startswith("automate"): r_type = "automate"
        elif res_name.startswith("internet_gateway"): r_type = "internet_gateway"
        else: continue # Should not happen
        
        # Get events for this resource if any
        res_events_raw = events_data.get(res_name, {}).get("events", [])
        
        # Parse events
        parsed_events = []
        for e in res_events_raw:
            try:
                # Format: "2026-01-07T16:02:08.815888"
                start = datetime.datetime.fromisoformat(e["timestamp_start_event"])
                # Duration is in what unit? Prompt sample: "duration_event": "21654654". 
                # That is ~250 days. 
                # Another sample: "7200" (2 hours). "1800" (30 mins).
                # Assuming SECONDS.
                duration_sec = float(e["duration_event"])
                end = start + datetime.timedelta(seconds=duration_sec)
                
                parsed_events.append({
                    "start_dt": start,
                    "end_dt": end,
                    "event_type": e["event_type"]
                })
            except Exception as err:
                print(f"Error parsing event for {res_name}: {err}")
        
        # Calculate
        energy_wh = calculate_energy_for_interval(r_type, start_date, end_date, parsed_events)
        co2_kg = (energy_wh / 1000.0) * CO2_PER_KWH
        
        summary_data["resources"][res_name] = {
            "type": r_type,
            "energy_wh": energy_wh,
            "co2_kg": co2_kg
        }
        summary_data["total_energy_wh"] += energy_wh
        summary_data["total_co2_kg"] += co2_kg

    return summary_data

def generate_reports(summary_data):
    print("Generating summary reports...")
    
    # Save JSON
    with open(SUMMARY_JSON, 'w') as f:
        json.dump(summary_data, f, indent=2)
        
    # Generate Textual Report using LLM
    prompt = f"""
    Based on the following energy consumption data for the last week, construct a detailed summary report.
    Data: {json.dumps(summary_data, indent=2)}
    
    The report should include:
    - Energy consumption per resource
    - CO2 emission per resource
    - Total energy consumption
    - Total CO2 emissions
    
    Format it clearly as a textual report.
    """
    
    report_text = get_llm_response(prompt, system_prompt="You are an energy auditor. Create a clear summary report.")
    
    with open(SUMMARY_TXT, 'w') as f:
        f.write(report_text)
        
    print(f"Reports saved to {SUMMARY_JSON} and {SUMMARY_TXT}")

def main():
    # 1. Load Input
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r') as f:
        events_data = json.load(f)
        
    # 2. Predict Failures (LLM)
    events_data_with_predictions = predict_failures(events_data)
    
    # 3. Store in DB
    with open(DB_FILE, 'w') as f:
        json.dump(events_data_with_predictions, f, indent=2)
    print(f"Events with predictions saved to {DB_FILE}")
    
    # 4. Calculate Energy & CO2
    summary_data = process_energy_calculations(events_data_with_predictions)
    
    # 5. Generate Reports
    generate_reports(summary_data)

if __name__ == "__main__":
    main()
