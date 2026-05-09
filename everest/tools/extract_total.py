import requests
from bs4 import BeautifulSoup
import csv
import re

URL = "https://services.totalenergies.tn/reseau-de-bornes-de-recharges-electriques"

def extract_coords(url):
    if not url:
        return None, None
    
    # Pattern 1: ?q=lat,lon
    match = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if match:
        return match.group(1), match.group(2)

    # Pattern 2: @lat,lon
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if match:
        return match.group(1), match.group(2)

    return None, None


def scrape():
    res = requests.get(URL)
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.find("table")
    rows = table.find_all("tr")[1:]

    data = []

    for row in rows:
        cols = row.find_all("td")

        name = cols[0].text.strip()
        stations = cols[1].text.strip()
        power = cols[2].text.strip()
        connector = cols[3].text.strip()
        points = cols[4].text.strip()

        link_tag = cols[5].find("a")
        map_url = link_tag["href"] if link_tag else None

        lat, lon = extract_coords(map_url)

        data.append({
            "station_name": name,
            "stations": stations,
            "power": power,
            "connector": connector,
            "points": points,
            "latitude": lat,
            "longitude": lon,
            "map_url": map_url
        })

    return data


def save_csv(data, filename="total_tunisia_ev.csv"):
    keys = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)


if __name__ == "__main__":
    data = scrape()
    save_csv(data)
    print(f"Saved {len(data)} stations")
