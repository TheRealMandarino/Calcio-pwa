import sqlite3
import json
import pandas as pd
import os
from backend.model import calculate_match_probabilities

def generate_league_json(db_path="data/database.db", output_dir="frontend"):
    conn = sqlite3.connect(db_path)
    today_str = "2026-10-26"
    
    # Estraiamo tutte le partite future raggruppate per lega
    query = f"""
        SELECT date, league, home_team, away_team 
        FROM matches 
        WHERE (home_goals IS NULL OR date >= ?) 
        ORDER BY league ASC, date ASC
    """
    df = pd.read_sql(query, conn, params=(today_str,))
    conn.close()
    
    if not df.empty and 'date' in df.columns:
        df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
        today_dt = pd.to_datetime(today_str)
        df = df[(df['date_parsed'] >= today_dt) | (df['date_parsed'].isna())]
    
    if df.empty:
        print("Nessuna partita futura trovata nel database.")
        return

    # Assicuriamoci che la cartella di output esista
    os.makedirs(output_dir, exist_ok=True)

    # Raggruppiamo le partite per campionato
    for league_name, group_df in df.groupby('league'):
        matches_output = []
        
        for _, row in group_df.iterrows():
            h_team = row['home_team']
            a_team = row['away_team']
            
            calc = calculate_match_probabilities(h_team, a_team, league=league_name)
            
            p1 = max(calc["prob_1"], 0.03)
            pX = max(calc["prob_X"], 0.03)
            p2 = max(calc["prob_2"], 0.03)
            
            total_p = p1 + pX + p2
            p1, pX, p2 = p1 / total_p, pX / total_p, p2 / total_p
            
            odd_1 = min(round(1.0 / p1, 2), 20.0)
            odd_X = min(round(1.0 / pX, 2), 20.0)
            odd_2 = min(round(1.0 / p2, 2), 20.0)
            
            matches_output.append({
                "date": str(row['date']),
                "league": league_name,
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
        
        # Creiamo un nome file pulito per il campionato (es. "ITA-Serie A" -> "ITA-Serie_A.json")
        safe_league_name = league_name.replace(" ", "_").lower()
        file_name = f"{safe_league_name}.json"
        output_path = os.path.join(output_dir, file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(matches_output, f, indent=4, ensure_ascii=False)
        
        print(f"File generato: {file_name} ({len(matches_output)} partite).")

if __name__ == "__main__":
    generate_league_json()