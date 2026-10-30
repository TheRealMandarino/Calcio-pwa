import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import poisson
from backend.stats import compute_team_stats
from backend.model import DixonColes_adjustment, calculate_match_probabilities

def run_backtest_exact_scores(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    
    # Selezioniamo solo le partite della stagione scorsa (es. 2025/2026) con risultato noto
    query = """
        SELECT date, league, home_team, away_team, home_goals, away_goals 
        FROM matches 
        WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL 
          AND date >= '2025-07-01' AND date <= '2026-06-30'
        ORDER BY date ASC
    """
    df_matches = pd.read_sql(query, conn)
    conn.close()
    
    if df_matches.empty:
        print("Nessuna partita trovata nel periodo specificato per il backtesting.")
        return

    total_matches = len(df_matches)
    exact_match_count = 0
    successful_samples = []  # Lista per raccogliere un campione di partite indovinate
    
    print(f"Avvio backtesting sul singolo risultato esatto più probabile per {total_matches} partite (Stagione 2025/2026)...")
    
    stats_cache = compute_team_stats(db_path)

    for _, row in df_matches.iterrows():
        h_team = row['home_team']
        a_team = row['away_team']
        real_score = f"{int(row['home_goals'])}-{int(row['away_goals'])}"
        league = row['league']
        match_date = row['date']
        
        try:
            calc = calculate_match_probabilities(h_team, a_team, league=league, precomputed_stats=stats_cache)
            exact_scores = calc.get("exact_scores", [])
            
            if not exact_scores:
                continue
                
            best_predicted = exact_scores[0]
            best_score = best_predicted["score"]
            best_odd = best_predicted["odd"]
            best_prob = best_predicted["probability"]
            
            if best_score == real_score:
                exact_match_count += 1
                # Salviamo i dettagli se abbiamo meno di 10 campioni
                if len(successful_samples) < 10:
                    successful_samples.append({
                        "date": match_date,
                        "league": league,
                        "match": f"{h_team} vs {a_team}",
                        "score": real_score,
                        "odd": best_odd,
                        "prob": best_prob
                    })
                
        except Exception as e:
            continue

    accuracy = (exact_match_count / total_matches) * 100 if total_matches > 0 else 0

    print("\n" + "="*55)
    print("REPORT BACKTESTING - SINGOLO RISULTATO ESATTO")
    print("="*55)
    print(f"Partite analizzate (Stagione scorsa): {total_matches}")
    print(f"Pronostici perfetti (#1 esatto)   : {exact_match_count}")
    print(f"Accuratezza sul singolo pronostico : {accuracy:.2f}%")
    print("="*55)
    
    if successful_samples:
        print("\nCAMPIONE DI 10 RISULTATI ESATTI INDOVINATI DAL MODELLO:")
        print("-" * 55)
        for idx, sample in enumerate(successful_samples, 1):
            print(f"{idx}. [{sample['date']}] {sample['league']} | {sample['match']}")
            print(f"   -> Risultato Reale: {sample['score']} | Quota: {sample['odd']} (Prob: {sample['prob']}%)")
            print("-" * 55)

if __name__ == "__main__":
    run_backtest_exact_scores()