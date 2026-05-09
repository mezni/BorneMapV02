import requests
import re

short_url = "https://goo.gl/maps/USq5nP6mqxJNRcbo9"

# Follow redirect
resp = requests.get(short_url, allow_redirects=True)
final_url = resp.url

print("Final URL:", final_url)

# Extract coordinates
match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
if match:
    lat, lon = match.group(1), match.group(2)
    print("Latitude:", lat)
    print("Longitude:", lon)
else:
    print("Coordinates not found")