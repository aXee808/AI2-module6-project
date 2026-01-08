import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "meta-llama/llama-3.1-70b-instruct"

SUMMARY_JSON = "summary_report.json"
ADVICE_TXT = "advice_report.txt"

def get_llm_response(prompt, system_prompt="You are a helpful AI assistant."):
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not found. Returning dummy response.")
        return "LLM Advice Unavailable: API Key missing."
    
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

def main():
    if not os.path.exists(SUMMARY_JSON):
        print(f"Error: {SUMMARY_JSON} not found. Run agent_monitor.py first.")
        return

    with open(SUMMARY_JSON, 'r') as f:
        summary_data = json.load(f)

    print("Analyzing summary report for advice...")
    
    # Identify Top 3 High Consumption Resources
    resources = summary_data.get("resources", {})
    sorted_resources = sorted(
        resources.items(), 
        key=lambda item: item[1].get("co2_kg", 0), 
        reverse=True
    )
    top_3_resources = dict(sorted_resources[:3])
    
    prompt = f"""
    Analyze the following carbon footprint summary report.
    
    Top 3 High Consumption Resources (Focus Area):
    {json.dumps(top_3_resources, indent=2)}
    
    Global Stats:
    Total Energy: {summary_data.get("total_energy_wh")} Wh
    Total CO2: {summary_data.get("total_co2_kg")} kg
    
    Task:
    Provide exactly 3 specific, actionable advices to reduce CO2 emissions.
    YOU MUST provide specific advice for EACH of the top 3 high consumption resources identified above.
    Explicitly mention the resource name (e.g., '{list(top_3_resources.keys())[0]}') in your advice.
    Explain the potential cause based on resource type and consumption, and propose a solution.
    """
    
    advice = get_llm_response(prompt, system_prompt="You are a Green IT consultant. Provide specific advice for high-consuming resources.")
    
    with open(ADVICE_TXT, 'w') as f:
        f.write(advice)
        
    print(f"Advice saved to {ADVICE_TXT}")

if __name__ == "__main__":
    main()
