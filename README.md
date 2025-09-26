# HackSpace Flight Data Summariser 🚀

A lightweight Python/Flask web app to transform and summarise flight data.  
It ingests raw flight/engine data, processes it (e.g. generating PIREPs, computing summary statistics), and presents a simple web interface for viewing results.

## Table of Contents

- [Features](#features)  
- [Architecture & Files](#architecture--files)  
- [Installation & Setup](#installation--setup)  
- [Usage](#usage)  
- [Endpoints & Flow](#endpoints--flow)  
- [Development & Testing](#development--testing)  
- [Dependencies](#dependencies)  
- [Contributing](#contributing)  
- [License & Acknowledgements](#license--acknowledgements)

## Features

- Convert raw engine data to PIREP (Pilot Report) format.  
- Summarise key flight metrics (e.g. average parameters, alerts)  
- Simple web UI to upload, view, or refresh data  
- Modular code separation (data processing, web routing, checks)  

## Architecture & Files

Here’s a rough breakdown of the important files and folders:

├── app.py # Main Flask application, routing logic
├── check.py # Validation / checks utilities
├── engToPIREP.py # Core transformation logic from engine to PIREP
├── templates/ # HTML templates
│ └── index.html # Main web UI
├── static/ # CSS or other static assets
│ └── css/
├── test1.py # Sample / test scripts
├── test2.html # Sample HTML for testing
├── requirements.txt # Python dependencies
└── .gitignore # Files/folders to ignore

markdown
Copy code

- `app.py` is the entry point and handles HTTP requests.  
- `check.py` contains helper functions to validate data or flag anomalies.  
- `engToPIREP.py` houses transformation logic (computations, mapping).  
- Templates + static are for the front-end display.  
- Test files serve as examples or quick sanity checks.

## Installation & Setup

1. **Clone the repository**  
   ```bash
   git clone https://github.com/shreshth410/hackspace_flight_data_summariser.git
   cd hackspace_flight_data_summariser
Set up a Python environment
It’s recommended to use a virtual environment:

bash
Copy code
python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
Install dependencies

bash
Copy code
pip install -r requirements.txt
Run the app

bash
Copy code
python app.py
By default, the Flask server should run on http://127.0.0.1:5000 (unless modified in code).

Usage
Open your browser and navigate to the base URL (e.g. http://127.0.0.1:5000).

Use the UI to upload flight data (in the supported raw format).

The app will process and render a summary / converted PIREP output.

You may also use API endpoints directly (see below) to automate processing from scripts.

Endpoints & Flow
Here’s a high-level flow of how data is processed:

Upload / Submit raw flight data via the web form or API call.

The request is handled by app.py, which calls the transformation logic in engToPIREP.py.

check.py is used at stages to validate, flag or correct anomalies.

Results are returned (or rendered via templates) to the user.

You can inspect app.py for exact route names and expected payload formats.

Development & Testing
Add new data formats or transformations in engToPIREP.py (isolated logic).

Use check.py to encapsulate validation rules to keep them separate from business logic.

You may create more test scripts (or adopt a testing framework like pytest) to validate functions.

To extend the UI, update templates in templates/ and static assets accordingly.

Dependencies
Some of the key dependencies (as in requirements.txt) may include:

Flask

(Any data-processing libraries you use: pandas, numpy, etc.)

(Other utilities as needed)

Be sure to update requirements.txt when you add new dependencies.

Contributing
Contributions are welcome! If you’d like to:

Fork the repository

Create a feature branch

Make your changes & test them

Submit a Pull Request

Please include a clear description of your changes, and ensure that existing functionality isn’t broken.

License & Acknowledgements
This project is [MIT-licensed / you can choose license]

Thanks to the flight-data / aerospace communities for domain inspiration.

Special mention to any libraries or resources you built upon.
