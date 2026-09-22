"""Export public, map-ready destination fields; no pandas dependency required."""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ['nature', 'adventure', 'history', 'photography', 'food', 'relaxation', 'family', 'shopping']
places = []
with (ROOT / 'data/processed/waxn_final_candidates.csv').open() as source:
    for row in csv.DictReader(source):
        try:
            lat, lng = float(row['latitude']), float(row['longitude'])
        except (ValueError, TypeError):
            continue
        if not (math.isfinite(lat) and math.isfinite(lng) and 5 <= lat <= 10 and 79 <= lng <= 83):
            continue
        if row['recommendation_eligible'] != 'True' or row['bad_name'] == 'True':
            continue
        places.append({
            'id': row['place_id'], 'name': row['name'], 'category': row['category'],
            'kind': row['subcategory'].replace('_', ' '), 'district': row['district'] or 'Other',
            'lat': lat, 'lng': lng, 'rating': float(row['avg_rating']) if row['avg_rating'] else None,
            'reviews': int(float(row['review_count'] or 0)),
            'quality': float(row['quality_score'] or 0), 'dataQuality': float(row['data_quality_score'] or 0),
            'scores': [float(row[f'{f}_score'] or 0) for f in FEATURES],
        })
output = ROOT / 'frontend/public/data/places.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(places, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
print(f'Exported {len(places):,} places to {output}')
