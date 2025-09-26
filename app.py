# In a new file called app.py
import os
import re
from flask import Flask, request, jsonify, render_template, redirect, url_for
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google AI with API key from environment variable
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

app = Flask(__name__)

try:
    # Try to import the PIREP converter
    from engToPIREP import convert_english_to_pirep
except Exception:
    convert_english_to_pirep = None

@app.get("/")
def index():
    # Render a single-input homepage
    return render_template("index.html")

@app.get("/icao")
def icao_get():
    return render_template("icao_input.html")

@app.post("/icao")
def icao_post():
    text = request.form.get("text", "").strip()
    pilot_profile = request.form.get("pilot_profile", "VFR").strip() or "VFR"
    if not text:
        return render_template("icao_input.html", error="Please enter 4-letter ICAO codes."), 400
    if not is_icao_list(text):
        return render_template("icao_input.html", error="Please enter valid 4-letter ICAO codes (e.g., VABB VOMM)."), 400
    codes = normalize_icao_list(text)
    metars_text = fetch_metars(codes)
    tafs_text = fetch_tafs(codes)
    hazards_text = fetch_sigmet_airmet(hours_before=6)
    combined_text = ''
    if metars_text:
        combined_text += 'METARs:\n' + metars_text + '\n\n'
    if tafs_text:
        combined_text += 'TAFs:\n' + tafs_text + '\n\n'
    if hazards_text:
        combined_text += 'Hazards(if any):\n' + hazards_text + '\n\n'
    stations = fetch_station_info(codes)
    summary_html = summarize_weather(combined_text.strip(), pilot_profile=pilot_profile, stations=stations)
    return render_template("summary.html", summary_html=summary_html, icao_codes=codes)

@app.get("/pirep")
def pirep_get():
    return render_template("pirep_input.html")

@app.post("/pirep")
def pirep_post():
    text = request.form.get("text", "").strip()
    if not text:
        return render_template("pirep_input.html", error="Please paste a report in plain English."), 400
    if convert_english_to_pirep is None:
        return render_template("pirep.html", pirep_text=None, error="PIREP conversion module not available."), 500
    try:
        pirep_line = convert_english_to_pirep(text)
    except Exception as e:
        return render_template("pirep_input.html", error=f"Error converting to PIREP: {e}"), 500
    return render_template("pirep.html", pirep_text=pirep_line, error=None)

def is_icao_list(text: str) -> bool:
    """Return True if the text appears to be a list of 4-letter ICAO codes."""
    if not text:
        return False
    cand = text.strip().upper()
    # Accept separators: commas and/or whitespace
    parts = re.split(r"[\s,]+", cand)
    parts = [p for p in parts if p]
    if not parts:
        return False
    # Each part must be exactly 4 alphabetic letters
    return all(re.fullmatch(r"[A-Z]{4}", p) for p in parts)

def normalize_icao_list(text: str):
    parts = re.split(r"[\s,]+", (text or "").strip().upper())
    return [p for p in parts if p]

@app.post("/process")
def process_input():
    """Decide whether the input is ICAO codes or free-text PIREP and route accordingly."""
    text = request.form.get("text", "").strip()
    pilot_profile = request.form.get("pilot_profile", "VFR").strip() or "VFR"
    if not text:
        # Back to index with an error message
        return render_template("index.html", error="Please enter ICAO codes or a PIREP in plain English."), 400

    if is_icao_list(text):
        # ICAO flow -> build summary and render summary page
        codes = normalize_icao_list(text)
        metars_text = fetch_metars(codes)
        tafs_text = fetch_tafs(codes)
        hazards_text = fetch_sigmet_airmet(hours_before=6)

        combined_text = ''
        if metars_text:
            combined_text += 'METARs:\n' + metars_text + '\n\n'
        if tafs_text:
            combined_text += 'TAFs:\n' + tafs_text + '\n\n'
        if hazards_text:
            combined_text += 'Hazards(if any):\n' + hazards_text + '\n\n'

        stations = fetch_station_info(codes)
        summary_html = summarize_weather(combined_text.strip(), pilot_profile=pilot_profile, stations=stations)
        return render_template("summary.html", summary_html=summary_html, icao_codes=codes)

    # Otherwise treat as free-text PIREP
    if convert_english_to_pirep is None:
        return render_template("pirep.html", pirep_text=None, error="PIREP conversion module not available."), 500

    try:
        pirep_line = convert_english_to_pirep(text)
    except Exception as e:
        return render_template("pirep.html", pirep_text=None, error=f"Error converting to PIREP: {e}"), 500

    return render_template("pirep.html", pirep_text=pirep_line, error=None)

def fetch_metars(icao_codes):
    """Fetch raw METAR data for the given ICAO codes using AviationWeather API."""
    if not icao_codes:
        return ""
    # Normalize and join codes
    codes = [c.strip().upper() for c in icao_codes if c.strip()]
    if not codes:
        return ""
    ids_param = ",".join(codes)
    url = f"https://aviationweather.gov/api/data/metar?format=raw&hours=2&ids={ids_param}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return ""
        text = resp.text.strip()
        return text
    except Exception:
        return ""

def fetch_station_info(icao_codes):
    """Fetch station (airport) names for given ICAO codes. Returns dict {ICAO: Name}."""
    if not icao_codes:
        return {}
    # Normalize list
    codes = [c.strip().upper() for c in icao_codes if c.strip()]
    if not codes:
        return {}
    base = "https://aviationweather.gov/dataserver_current/httpparam"
    params = {
        "datasource": "stations",
        "requesttype": "retrieve",
        "format": "json",
        "stationstring": ",".join(codes)
    }
    try:
        r = requests.get(base, params=params, headers={"Accept": "application/json"}, timeout=10)
        if r.status_code != 200:
            return {c: "" for c in codes}
        j = r.json()
        # Response can be under 'features' (GeoJSON) or 'data' list
        data = j.get('features') or j.get('stations', {}).get('data') or []
        out = {}
        if isinstance(data, list):
            for item in data:
                props = item.get('properties') if isinstance(item, dict) else item
                if not isinstance(props, dict):
                    continue
                icao = (props.get('station_id') or props.get('icao_site') or props.get('icao_code') or "").upper()
                name = props.get('site') or props.get('station_name') or props.get('name') or ""
                if icao:
                    out[icao] = name
        # Ensure all requested codes are present
        for c in codes:
            out.setdefault(c, "")
        return out
    except Exception:
        return {c: "" for c in codes}

def fetch_station_coords(icao_codes):
    """Fetch lat/lon for given ICAO codes. Returns list of dicts: {icao, name, lat, lon}."""
    if not icao_codes:
        return []
    codes = [c.strip().upper() for c in icao_codes if c and c.strip()]
    if not codes:
        return []
    base = "https://aviationweather.gov/dataserver_current/httpparam"
    params = {
        "datasource": "stations",
        "requesttype": "retrieve",
        "format": "json",
        "stationstring": ",".join(codes)
    }
    try:
        r = requests.get(base, params=params, headers={"Accept": "application/json"}, timeout=10)
        r.raise_for_status()
        j = r.json()
        data = j.get('features') or j.get('stations', {}).get('data') or []
        out = []
        seen = set()
        if isinstance(data, list):
            for item in data:
                props = item.get('properties') if isinstance(item, dict) else item
                if not isinstance(props, dict):
                    continue
                icao = (props.get('station_id') or props.get('icao_site') or props.get('icao_code') or "").upper()
                if not icao or icao in seen:
                    continue
                seen.add(icao)
                name = props.get('site') or props.get('station_name') or props.get('name') or ""
                # Robust lat/lon extraction from properties first
                lat = props.get('latitude') or props.get('lat') or props.get('latitude_deg') or props.get('latitude_degN')
                lon = props.get('longitude') or props.get('lon') or props.get('longitude_deg') or props.get('longitude_degE')
                # If still missing, try GeoJSON geometry.coordinates [lon, lat]
                if (lat is None or lon is None) and isinstance(item, dict):
                    geom = item.get('geometry') or {}
                    coords = geom.get('coordinates') if isinstance(geom, dict) else None
                    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                        lon = coords[0] if lon is None else lon
                        lat = coords[1] if lat is None else lat
                try:
                    lat = float(lat) if lat is not None else None
                    lon = float(lon) if lon is not None else None
                except Exception:
                    lat, lon = None, None
                out.append({"icao": icao, "name": name, "lat": lat, "lon": lon})
        # Fill missing coords via a conservative OSM Nominatim fallback
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "ApacheAI-Weather-Briefer/1.0 (contact: local)"
            })
            for rec in out:
                if rec.get('lat') is None or rec.get('lon') is None:
                    q = f"airport {rec.get('icao','')}"
                    try:
                        nom = session.get(
                            "https://nominatim.openstreetmap.org/search",
                            params={"format": "json", "q": q, "limit": 1},
                            timeout=8
                        )
                        if nom.status_code == 200:
                            arr = nom.json()
                            if isinstance(arr, list) and arr:
                                rec['lat'] = float(arr[0]['lat'])
                                rec['lon'] = float(arr[0]['lon'])
                    except Exception:
                        pass
        except Exception:
            pass

        # Ensure requested order
        order = {c: i for i, c in enumerate(codes)}
        out.sort(key=lambda x: order.get(x.get('icao', ''), 1e9))
        return out
    except Exception:
        # Return placeholders with no coords
        return [{"icao": c, "name": "", "lat": None, "lon": None} for c in codes]

def fetch_sigmet_airmet(hours_before=6):
    """Fetch active SIGMETs and AIRMETs from AviationWeather ADDS Data Server (JSON)."""
    base = "https://aviationweather.gov/dataserver_current/httpparam"
    headers = {"Accept": "application/json"}
    pieces = []
    try:
        # SIGMETs
        sig_params = {
            "datasource": "sigmet",
            "requesttype": "retrieve",
            "format": "json",
            "hoursBeforeNow": str(hours_before)
        }
        r1 = requests.get(base, params=sig_params, headers=headers, timeout=10)
        if r1.status_code == 200:
            j = r1.json()
            data = j.get('features') or j.get('sigmet', {}).get('data') or []
            # Some responses use GeoJSON under 'features', others nested under 'data'
            if isinstance(data, list) and data:
                texts = []
                for item in data:
                    props = item.get('properties') if isinstance(item, dict) else item
                    txt = (props or {}).get('raw_text') or (props or {}).get('description')
                    if txt:
                        texts.append(txt)
                if texts:
                    pieces.append("SIGMETs:\n" + "\n".join(texts))
        # AIRMETs (including G-AIRMET)
        air_params = {
            "datasource": "airsigmets",
            "requesttype": "retrieve",
            "format": "json",
            "hoursBeforeNow": str(hours_before)
        }
        r2 = requests.get(base, params=air_params, headers=headers, timeout=10)
        if r2.status_code == 200:
            j = r2.json()
            data = j.get('features') or j.get('airsigmet', {}).get('data') or []
            if isinstance(data, list) and data:
                texts = []
                for item in data:
                    props = item.get('properties') if isinstance(item, dict) else item
                    txt = (props or {}).get('raw_text') or (props or {}).get('hazard') or (props or {}).get('message')
                    if txt:
                        texts.append(txt)
                if texts:
                    pieces.append("AIRMETs:\n" + "\n".join(texts))
    except Exception:
        return ""
    return "\n\n".join(pieces).strip()

def fetch_tafs(icao_codes):
    """Fetch raw TAF data for the given ICAO codes using AviationWeather API."""
    if not icao_codes:
        return ""
    codes = [c.strip().upper() for c in icao_codes if c.strip()]
    if not codes:
        return ""
    ids_param = ",".join(codes)
    url = f"https://aviationweather.gov/api/data/taf?format=raw&hours=24&ids={ids_param}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return ""
        return resp.text.strip()
    except Exception:
        return ""

def summarize_weather(weather_data, pilot_profile, stations):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Build a simple ICAO -> Name directory for the prompt
        airport_directory = "\n".join([f"{k}: {v}" if v else f"{k}:" for k, v in stations.items()])

        prompt = f"""
        You are an expert aviation weather briefer. Audience pilot profile: '{pilot_profile}'.
        Read the RAW WEATHER DATA and the AIRPORT DIRECTORY and produce three sections only, as concise HTML:
        1) <section id="summary"><h2>Summary</h2><ul><li>...</li></ul></section>
        2) <section id="recommendations"><h2>Recommendations</h2><ul><li>...</li></ul></section>
        3) <section id="per-airport"><h2>Per-Airport Conditions</h2>
             <ul>
               <li><strong>VABB - Chhatrapati Shivaji Intl</strong>: decoded current conditions, ceilings/visibility, winds, precip, hazards; brief TAF outlook.</li>
               <li><strong>VOMM - Chennai Intl</strong>: ...</li>
             </ul>
           </section>

        - Keep bullets brief and safety-forward.
        - No preamble or explanations outside these sections.
        - Do not include the raw data itself in your output. Decode it to plain language.
        - When showing Per-Airport Conditions, make it so that every individual feature is shown in a new line, along with a bullet point.
        - Make the summaries be 1-2 sentences only. Include any values that are of value to the pilot. 
        - Also, In the recommendations section, I want you to summarise the journey into various legs. If there are two airports, I want to see the weather report for the journey between them
        - In case there are multiple airports, then i want to see the weather report from airport 1 to 2, then 2 to 3, then 3 to 4 and so on.

        AIRPORT DIRECTORY (ICAO -> Name):
        {airport_directory}

        RAW WEATHER DATA START
        {weather_data}
        RAW WEATHER DATA END
        """

        response = model.generate_content(prompt)
        raw_html = (response.text or '').strip()

        # Normalize HTML into strict sections with IDs so the front-end toggle works reliably
        def normalize_sections(html: str) -> str:
            try:
                from html.parser import HTMLParser
            except Exception:
                HTMLParser = None

            # Fast-path: if all three IDs exist, keep as-is
            if all(x in html for x in ['id="summary"', 'id="recommendations"', 'id="per-airport"']):
                return html

            # Heuristic wrapper: search for headings and wrap nearby content
            # Keep it simple to avoid extra deps; operate with string finds.
            def extract_block(src: str, heading: str, sec_id: str) -> (str, str):
                idx = src.lower().find(f">{heading.lower()}<")
                if idx == -1:
                    # Try with quotes, loose match
                    idx = src.lower().find(heading.lower())
                if idx == -1:
                    return '', src
                # Backtrack to enclosing heading tag start
                start_h = src.rfind('<', 0, idx)
                if start_h == -1:
                    return '', src
                # Take from heading start until next heading of same level or end
                # Simplify: split remainder by next <h1 or <h2 tag
                rem = src[start_h:]
                end_pos = len(rem)
                for tag in ['<h1', '<h2']:
                    nxt = rem.find(tag, 1)
                    if nxt != -1:
                        end_pos = min(end_pos, nxt)
                block = rem[:end_pos]
                # Remove block from src
                new_src = src[:start_h] + rem[end_pos:]
                # Wrap block
                wrapped = f'<section id="{sec_id}">{block}</section>'
                return wrapped, new_src

            src = html
            out_parts = []
            # Extract Summary
            summary_block, src = extract_block(src, 'Summary', 'summary')
            if summary_block:
                out_parts.append(summary_block)
            # Extract Recommendations
            recs_block, src = extract_block(src, 'Recommendations', 'recommendations')
            if recs_block:
                out_parts.append(recs_block)
            # Whatever remains becomes per-airport
            remainder = src.strip()
            if remainder:
                out_parts.append(f'<section id="per-airport">{remainder}</section>')
            return '\n'.join(out_parts)

        return normalize_sections(raw_html)
    except Exception as e:
        return f"Error generating summary: {str(e)}"

@app.route('/summarize', methods=['POST'])
def handle_summarize():
    try:
        data = request.get_json()
        if not data or 'icao_codes' not in data:
            return jsonify({'error': 'Missing icao_codes in request'}), 400

        # Parse comma-separated ICAO codes
        icao_raw = data.get('icao_codes', '')
        codes = [c.strip().upper() for c in icao_raw.split(',') if c.strip()]
        if not codes:
            return jsonify({'error': 'No valid ICAO codes provided'}), 400

        pilot_profile = data.get('pilot_profile', 'general')  # Optional

        # Fetch METAR, TAF, and hazard data
        metars_text = fetch_metars(codes)
        tafs_text = fetch_tafs(codes)
        hazards_text = fetch_sigmet_airmet(hours_before=6)
        if not metars_text and not tafs_text and not hazards_text:
            return jsonify({'error': 'Failed to fetch METAR/TAF/AIRMET/SIGMET data'}), 502

        combined_text = ''
        if metars_text:
            combined_text += 'METARs:\n' + metars_text + '\n\n'
        if tafs_text:
            combined_text += 'TAFs:\n' + tafs_text + '\n\n'
        if hazards_text:
            combined_text += 'Hazards(if any):\n' + hazards_text + '\n\n'

        # Get airport names for decoding and display inside the model output
        stations = fetch_station_info(codes)

        # Ask model for Summary, Recommendations, and Per-Airport Conditions (HTML snippet)
        summary_html = summarize_weather(combined_text.strip(), pilot_profile, stations)

        # Final HTML contains only decoded sections (no raw metadata shown)
        final_html = f"""
        <div class=\"weather-brief\">
          {summary_html}
        </div>
        """.strip()

        # Keep response key 'summary' for compatibility with the front-end, but it now contains HTML
        return jsonify({'summary': final_html})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.post('/api/coords')
def api_coords():
    try:
        data = request.get_json() or {}
        codes = data.get('icao_codes') or []
        if isinstance(codes, str):
            codes = [c.strip().upper() for c in codes.split(',') if c.strip()]
        coords = fetch_station_coords(codes)
        return jsonify({"coords": coords})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)