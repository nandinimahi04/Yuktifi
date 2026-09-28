from __future__ import annotations
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'backend/data/raw/census/2011-IndiaStateDistSbDistVill-0000.xlsx'
URL='https://censusindia.gov.in/nada/index.php/catalog/42554/download/46180/2011-IndiaStateDistSbDistVill-0000.xlsx'
TARGET.parent.mkdir(parents=True,exist_ok=True)
print('Downloading official Census PCA 2011...')
try:
    urllib.request.urlretrieve(URL, TARGET)
except Exception as e:
    raise SystemExit(f'Download failed. Download manually from {URL} and place it at {TARGET}: {e}')
print(f'Saved {TARGET}')
