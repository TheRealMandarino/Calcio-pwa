import sqlite3
import json
import pandas as pd
from datetime import datetime
from backend.model import calculate_match_probabilities

def generate_partite_json(output_path="frontend/partite.json", db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    
    # Data odierna di riferimento (26 Ottobre 2026)
    today_str = "2026-10-26"
    
    # Estraiamo solo le partite future o odierne (senza gol registrati o con data >= oggi)
    query = f"""
        SELECT date, home_team, away_team 
        FROM matches 
        WHERE (home_goals IS NULL OR date >= ?) 
        ORDER BY date ASC
    """
    df = pd.read_sql(query, conn, params=(today_str,))
    conn.close()
    
    # Fallback di sicurezza: se la query SQL non filtra abbastanza per formato data, filtriamo con pandas
    if not df.empty and 'date' in df.columns:
        df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
        today_dt = pd.to_datetime(today_str)
        # Filtriamo le partite dalla data odierna in poi (o con data non parsabile per sicurezza)
        df = df[(df['date_parsed'] >= today_dt) | (df['date_parsed'].isna())]
    
    matches_output = []
    
    for _, row in df.iterrows():
        h_team = row['home_team']
        a_team = row['away_team']
        
        calc = calculate_match_probabilities(h_team, a_team)
        
        # Floor di probabilità al 3%
        p1 = max(calc["prob_1"], 0.03)
        pX = max(calc["prob_X"], 0.03)
        p2 = max(calc["prob_2"], 0.03)
        
        # Rinormalizzazione post-floor
        total_p = p1 + pX + p2
        p1, pX, p2 = p1 / total_p, pX / total_p, p2 / total_p
        
        # Calcolo quote con tetto massimo bloccato a 20.0 nel backend
        odd_1 = min(round(1.0 / p1, 2), 20.0)
        odd_X = min(round(1.0 / pX, 2), 20.0)
        odd_2 = min(round(1.0 / p2, 2), 20.0)
        
        matches_output.append({
            "date": str(row['date']),
            "home_team": h_team,
            "away_team": a_team,
            "lambda_home": calc["lambda_home"],
            "lambda_away": calc["lambda_away"],
            "probabilities": {
                "1": round(p1 * 100, 1),
                "X": round(pX * 100, 1),
                "2": round(p2 * 100, 1)
            },
            "odds": {
                "1": odd_1,
                "X": odd_X,
                "2": odd_2
            }
        })
        
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matches_output, f, indent=4, ensure_ascii=False)
    
    print(f"File {output_path} generato con successo ({len(matches_output)} partite future analizzate).")

if __name__ == "__main__":
    generate_partite_json()