import os
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
import numpy as np
from time_mapping import time_mapping
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from twilio.rest import Client
from dotenv import load_dotenv

# Laad de .env-variabelen
load_dotenv(override=True)

# Controleer specifieke variabelen
print(f"Login URL: {os.getenv('login_url')}")
print(f"Username: {os.getenv('username')}")
print(f"Password: {os.getenv('password')}")
print(f"Cloud Name: {os.getenv('cloud_name')}")

# Configuratie ophalen uit environment variables
login_url = os.getenv("login_url")
username = os.getenv("username")
password = os.getenv("password")

# Controleer of alle vereiste environment variables aanwezig zijn
if not all([login_url, username, password]):
    raise EnvironmentError("Een of meer vereiste configuratievariabelen ontbreken!")

# Browser starten
driver = webdriver.Chrome()

# URL openen
driver.get(login_url)

# Gebruikersnaam invullen
username_field = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "username"))
)
username_field.send_keys(username)

# Klik op de "Ga verder"-knop
next_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-btn"))  # Pas selector aan
)
next_button.click()

# Wacht tot het wachtwoordveld geladen is
password_field = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "outlined-adornment-password"))  # Pas selector aan
)
password_field.send_keys(password)

# Klik op de login-knop
login_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-btn"))  # Pas selector aan
)
login_button.click()

# Wacht tot de barchart geladen is
WebDriverWait(driver, 30).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "path.apexcharts-bar-area"))
)

# HTML van de pagina ophalen
page_source = driver.page_source
soup = BeautifulSoup(page_source, "html.parser")

# Zoek alle barchart-elementen
bars = soup.select("path.apexcharts-bar-area")

# Data scrapen
prices = []
for bar in bars:
    j_value = bar.get("j")  # Haal de tijdindex op
    price_value = bar.get("val")  # Haal de prijs op
    if j_value and price_value:
        j_index = int(j_value)
        prices.append({
            "time": time_mapping.get(j_index, f"Unknown index {j_index}"),
            "price": float(price_value)
        })

# Browser sluiten
driver.quit()

# Schrijf alleen de eerste 24 rijen naar een CSV-bestand
if prices:
    with open("energy_prices.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["time", "price"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(prices[:24])  # Schrijf alleen de eerste 24 rijen

    print("Eerste 24 rijen succesvol opgeslagen in energy_prices.csv")

    # Maak een grafiek van de prijzen met soepele lijnen
    times = [item['time'] for item in prices[:24]]
    price_values = [item['price'] for item in prices[:24]]

    # Converteer indices naar numerieke waarden voor interpolatie
    x = np.arange(len(times))
    y = np.array(price_values)

    # Maak een interpolatiefunctie
    x_new = np.linspace(x.min(), x.max(), 300)  # Meer punten voor gladde lijn
    spline = make_interp_spline(x, y, k=3)  # Cubic spline
    y_smooth = spline(x_new)

    # Minimalistische grafiekstijl
    plt.figure(figsize=(12, 6))
    plt.plot(x_new, y_smooth, color="#A0522D", linewidth=2.5)  # Aardetint kleur
    plt.title('Energieprijzen per uur', fontsize=18, weight='bold', color="#333333")
    plt.xlabel('Tijd', fontsize=14, color="#555555")
    plt.ylabel('Prijs (€)', fontsize=14, color="#555555")
    plt.xticks(ticks=x, labels=times, rotation=45, fontsize=12, color="#555555")
    plt.yticks(fontsize=12, color="#555555")
    plt.grid(visible=False)  # Geen raster voor minimalisme
    plt.tight_layout()

    # Grafiek opslaan
    graph_filename = "energy_prices.png"
    plt.savefig(graph_filename)
    print(f"Grafiek opgeslagen als {graph_filename}")
else:
    print("Geen geldige data gevonden om op te slaan.")

# Controleer of het bestand bestaat
if not os.path.exists(graph_filename):
    print(f"Bestand niet gevonden: {graph_filename}")
else:
    # Cloudinary configuratie ophalen uit environment variables
    cloudinary.config(
        cloud_name=os.getenv("cloud_name"),
        api_key=os.getenv("api_key"),
        api_secret=os.getenv("api_secret"),
        secure=True
    )

    # Upload de afbeelding naar Cloudinary
    upload_result = cloudinary.uploader.upload(
        graph_filename,
        public_id="energy_prices",
        overwrite=True,
        resource_type="image"
    )

    # Print de veilige URL van de afbeelding
    secure_url = upload_result["secure_url"]
    print(f"Afbeelding geüpload: {secure_url}")

    # Optimaliseer de afbeelding voor web
    optimized_url, _ = cloudinary_url(
        "energy_prices",
        fetch_format="auto",
        quality="auto"
    )
    print(f"Geoptimaliseerde URL: {optimized_url}")


## # Twilio configuratie ophalen uit environment variables
## account_sid = os.getenv("account_sid")
## auth_token = os.getenv("auth_token")
## client = Client(account_sid, auth_token)
## 
## # Datum van morgen ophalen en formatteren
## tomorrow_date = (datetime.now().strftime("%d-%m-%Y"))  # + timedelta(days=1)).strftime("%d-%m-%Y")
## 
## # WhatsApp-bericht verzenden met de datum van morgen
## message = client.messages.create(
##     from_="whatsapp:+14155238886",  # Twilio's WhatsApp-sandboxnummer
##     to="whatsapp:+31614967078",  # Jouw telefoonnummer in internationaal formaat
##     body=f"Dit zijn de energieprijzen voor {tomorrow_date}!",  # Berichttekst met datum van morgen
##     media_url=[secure_url]  # De URL van de Cloudinary-afbeelding
## )
## print(f"Bericht verzonden: {message.sid}")
