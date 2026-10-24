import requests
import csv
import io
import json

STAGIONI = ["2122", "2223", "2324", "2425", "2526", "2627"]

tutte_le_partite = []

for stagione in STAGIONI:
    url = f"https://www.football-data.co.uk/mmz4281/{stagione}/I1.csv"
    print(f"Scaricamento stagione {stagione}...")
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            f = io.StringIO(response.text)
            reader = csv.DictReader(f)
            
            count = 0
            for row in reader:
                data = row.get('Date', '')
                home = row.get('HomeTeam', '')
                away = row.get('AwayTeam', '')
                h_gol = row.get('FTHG', None)
                a_gol = row.get('FTAG', None)
                
                if home and away:
                    tutte_le_partite.append({
                        "stagione": stagione,
                        "squadra_casa": home,
                        "squadra_ospite": away,
                        "data": data,
                        "squadra_casa_gol": h_gol if h_gol != "" else None,
                        "squadra_ospite_gol": a_gol if a_gol != "" else None
                    })
                    count += 1
            print(f">>> Stagione {stagione}: importate {count} partite.")
        else:
            print(f">>> Stagione {stagione} non ancora disponibile o errore (HTTP {response.status_code})")
            
    except Exception as e:
        print(f">>> Errore per la stagione {stagione}: {e}")

# Salvataggio nel file JSON finale compatibile con la PWA
with open('partite.json', 'w', encoding='utf-8') as f:
    json.dump(tutte_le_partite, f, ensure_ascii=False, indent=4)

print(f"\nTotale partite salvate in partite.json: {len(tutte_le_partite)}")