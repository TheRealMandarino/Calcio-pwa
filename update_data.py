import json
import soccerdata as sd
import pandas as pd

stagioni = ["2122", "2223", "2324", "2425", "2526", "2627"]
tutte_le_partite = []

for stagione in stagioni:
    try:
        print(f"Scaricamento stagione {stagione}...")
        sa = sd.FBref(leagues="ITA-Serie A", seasons=stagione)
        schedule = sa.read_schedule()
        
        for idx, row in schedule.iterrows():
            h_gol = None
            a_gol = None
            
            # 1. Tentativo con colonne separate se presenti
            if 'home_score' in schedule.columns and 'away_score' in schedule.columns:
                h_gol = row.get('home_score')
                a_gol = row.get('away_score')
            
            # 2. Tentativo se i gol sono dentro una colonna 'score' (es. "2-1" o "2–1")
            if (pd.isna(h_gol) or pd.isna(a_gol)) and 'score' in schedule.columns:
                score_val = row.get('score')
                if pd.notna(score_val) and isinstance(score_val, str):
                    # Gestisce trattini normali o unicode
                    score_val = score_val.replace('–', '-')
                    if '-' in score_val:
                        parts = score_val.split('-')
                        if len(parts) == 2 and parts[0].strip().isdigit():
                            h_gol = parts[0].strip()
                            a_gol = parts[1].strip()

            tutte_le_partite.append({
                "stagione": stagione,
                "squadra_casa": str(row.get('home_team', 'Casa')),
                "squadra_ospite": str(row.get('away_team', 'Ospite')),
                "data": str(row.get('date', '')),
                "squadra_casa_gol": h_gol,
                "squadra_ospite_gol": a_gol
            })
    except Exception as e:
        print(f"Errore per la stagione {stagione}: {e}")

with open('partite.json', 'w', encoding='utf-8') as f:
    json.dump(tutte_le_partite, f, ensure_ascii=False, indent=4)

print(f"Totale partite salvate: {len(tutte_le_partite)}")