import json
import soccerdata as sd
import pandas as pd

# Elenco delle stagioni da scaricare (formato FBref per soccerdata)
stagioni = ["2122", "2223", "2324", "2425", "2526", "2627"]

tutte_le_partite = []

for stagione in stagioni:
    try:
            print(f"Scaricamento stagione {stagione}...")
                    sa = sd.FBref(leagues="ITA-Serie A", seasons=stagione)
                            schedule = sa.read_schedule()
                                    
                                            for idx, row in schedule.iterrows():
                                                        tutte_le_partite.append({
                                                                        "stagione": stagione,
                                                                                        "squadra_casa": str(row.get('home_team', 'Casa')),
                                                                                                        "squadra_ospite": str(row.get('away_team', 'Ospite')),
                                                                                                                        "data": str(row.get('date', ''))
                                                                                                                                    })
                                                                                                                                        except Exception as e:
                                                                                                                                                print(f"Errore per la stagione {stagione}: {e}")

                                                                                                                                                # Salva tutto nello storico JSON per la PWA
                                                                                                                                                with open('partite.json', 'w', encoding='utf-8') as f:
                                                                                                                                                    json.dump(tutte_le_partite, f, ensure_ascii=False, indent=4)

                                                                                                                                                    print(f"Totale partite salvate: {len(tutte_le_partite)}")
                                                                                                                                                    