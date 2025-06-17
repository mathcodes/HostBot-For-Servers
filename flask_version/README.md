# Create the Flask HostBot directory structure

# 1. Create main project directory
mkdir hostbot
cd hostbot

# 2. Create templates directory
mkdir templates

# 3. Create files
# Copy app.py content to this file
touch app.py

# Copy requirements.txt content to this file  
touch requirements.txt

# Copy index.html content to this file
touch templates/index.html

# Copy README.md content to this file
touch README.md

# 4. Set up virtual environment
python -m venv venv

# 5. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Run the application
python app.py

# Your Flask app will be available at: http://localhost:5000

# Final directory structure should look like:
# hostbot/
# ├── venv/              # Virtual environment (created by python -m venv)
# ├── app.py             # Main Flask application
# ├── requirements.txt   # Python dependencies
# ├── templates/
# │   └── index.html     # Main template file
# └── README.md          # Setup instructions