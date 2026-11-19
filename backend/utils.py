import zipfile
from bs4 import BeautifulSoup
import pandas as pd

def parse_kmz_file(file_path: str):
    data = []
    with zipfile.ZipFile(file_path, 'r') as z:
        for filename in z.namelist():
            if filename.endswith('.kml'):
                with z.open(filename) as f:
                    soup = BeautifulSoup(f, 'html.parser')
                    for coords in soup.find_all('coordinates'):
                        data.append(coords.text.strip())
    return data
