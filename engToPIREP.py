import google.generativeai as genai
import os
from datetime import datetime

def convert_english_to_pirep(user_text: str, fields: dict | None = None) -> str:
    """
    Convert a free-text pilot report into a single-line standardized PIREP string using Gemini.

    Requires GEMINI_API_KEY (or GOOGLE_API_KEY) in environment.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    current_time = datetime.utcnow().strftime("%H%MZ")

    # Prepare a structured-fields snippet to bias/assist the model.
    fields = fields or {}
    problem_type = (fields.get('problem_type') or '').strip()
    location = (fields.get('location') or '').strip()
    aircraft_model = (fields.get('aircraft_model') or '').strip()
    altitude = (fields.get('altitude') or '').strip()

    prompt = f'''
    You are an expert in aviation communications. Translate the provided plain-English pilot report
    into a single-line standardized PIREP string.

    You are also given STRUCTURED FIELDS captured from a form. When a field is present there,
    prefer it over any conflicting interpretation from free text. If a field is blank, you may
    infer from the free text. Omit segments that cannot be inferred at all.

    Provided Text:
    """
    {user_text}
    """

    Structured Fields (prefer these when present):
      - Problem Type: {problem_type}
      - Location (ICAO or relative): {location}
      - Aircraft Model: {aircraft_model}
      - Altitude: {altitude}

    Current UTC time: {current_time}

    Output rules:
    1) Report type: 'UUA' for urgent hazards (severe turbulence/icing, LLWS, volcanic ash, hail, TS), else 'UA'.
    2) Location: /OV [ICAO or relative]. If an airport name is clear, convert to ICAO.
    3) Time: /TM [HHMMZ]. Use {current_time} unless a precise time is clearly given.
    4) Altitude: /FL [hundreds of feet, 3 digits].
    5) Aircraft: /TP [standard code] if inferable.
    6) Sky cover: /SK [codes+alt] (e.g., BKN080, SCT030, CB) if inferable.
    7) Weather: /WX [codes] (e.g., RA, BR, +SHRA, LTG) if inferable.
    8) Temperature: /TA [C], with M for negative (e.g., M02), if inferable.
    9) Turbulence: /TB [intensity/type] if inferable.
    10) Icing: /IC [intensity/type] if inferable.

    Output a SINGLE LINE with only the coded PIREP segments separated by spaces, no extra commentary.
    Example: UUA /OV VIDP /TM {current_time} /FL080 /TP C172 /SK BKN080 /WX BR /TB LGT CHOP /IC NEG
    '''

    response = model.generate_content(prompt)
    return (response.text or "").strip()

def main():
    """
    Main function to convert an English pilot report (PIREP) to a standardized string format.
    """
    try:
        print("Please provide a pilot report in plain English.")
        pirep_text = input("Enter your report: ")

        print("\nConverting English report to PIREP...")
        pirep_line = convert_english_to_pirep(pirep_text)

        print("\n--- PIREP ---")
        print(pirep_line)

    except Exception as e:
        print("\nAn error occurred:")
        print(f"Details: {e}")
        print("\nPlease check your API key, internet connection, and quota limits.")

if __name__ == "__main__":
    main()