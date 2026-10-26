import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import poisson
from backend.stats import compute_team_stats
from backend.model import DixonColes_adjustment

def run_backtest(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    query = """
        SELECT date, league, home_team, away_team, home_goals, away_goals 
        FROM matches 
        WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
        ORDER BY date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        print("Nessuna partita completata trovata per il backtesting.")
        return

    print(f"Avvio backtesting ottimizzato su {len(df)} partite storiche...")
    
    # Calcoliamo le statistiche una sola volta all'inizio (velocissimo)
    attack, defense, league_avg_h, league_avg_a, global_avg_h, global_avg_a = compute_team_stats(db_path)
    
    results_by_league = {}

    for _, row in df.iterrows():
        league = row['league']
        h_team = row['home_team']
        a_team = row['away_team']
        h_actual = int(row['home_goals'])
        a_actual = int(row['away_goals'])
        
        if h_actual > a_actual:
            actual_outcome = "1"
        elif h_actual == a_actual:
            actual_outcome = "X"
        else:
            actual_outcome = "2"
            
        avg_h = league_avg_h.get(league, global_avg_h)
        avg_a = league_avg_a.get(league, global_avg_a)
        
        att_h = attack.get(h_team, 1.0)
        def_h = defense.get(h_team, 1.0)
        att_a = attack.get(a_team, 1.0)
        def_a = defense.get(a_team, 1.0)
        
        # Parametri specifici lega (inclusi i correttivi Bundesliga)
        if league == "GER-Bundesliga":
            home_advantage = 1.02
            rho = -0.05
            max_goals = 9
        else:
            home_advantage = 1.04
            rho = -0.11
            max_goals = 7

        lambda_home = max(att_h * def_a * avg_h * home_advantage, 0.70)
        lambda_away = max(att_a * def_h * avg_a, 0.65)
        
        matrix = np.zeros((max_goals, max_goals))
        for i in range(max_goals):
            for j in range(max_goals):
                p_home = poisson.pmf(i, lambda_home)
                p_away = poisson.pmf(j, lambda_away)
                dc = DixonColes_adjustment(i, j, lambda_home, lambda_away, rho)
                matrix[i, j] = p_home * p_away * max(dc, 0.0)
                
        matrix /= np.sum(matrix)
        
        prob_1 = np.sum(np.tril(matrix, -1))
        prob_X = np.sum(np.diag(matrix))
        prob_2 = np.sum(np.triu(matrix, 1))
        
        total = prob_1 + prob_X + prob_2
        if total > 0:
            prob_1, prob_X, prob_2 = prob_1/total, prob_X/total, prob_2/total
        else:
            prob_1, prob_X, prob_2 = 0.33, 0.34, 0.33
            
        probs = {"1": prob_1, "X": prob_X, "2": prob_2}
        predicted_outcome = max(probs, key=probs.get)
        
        if league not in results_by_league:
            results_by_league[league] = {"total": 0, "correct": 0, "profit_flat": 0.0}
            
        results_by_league[league]["total"] += 1
        
        is_correct = (predicted_outcome == actual_outcome)
        if is_correct:
            results_by_league[league]["correct"] += 1
            
        model_prob = probs[predicted_outcome]
        implied_odd = 1.0 / model_prob if model_prob > 0 else 1.0
        
        if is_correct:
            results_by_league[league]["profit_flat"] += (implied_odd - 1.0)
        else:
            results_by_league[league]["profit_flat"] -= 1.0

    print("\n" + "="*50)
    print("      REPORT FINALE BACKTESTING (OTTIMIZZATO)")
    print("="*50)
    
    global_tot = 0
    global_corr = 0
    
    for league, data in results_by_league.items():
        tot = data["total"]
        corr = data["correct"]
        acc = (corr / tot) * 100 if tot > 0 else 0
        profit = data["profit_flat"]
        roi = (profit / tot) * 100 if tot > 0 else 0
        
        global_tot += tot
        global_corr += corr
        
        print(f"\n🏆 Campionato: {league}")
        print(f"   • Partite testate: {tot}")
        print(f"   • Pronostici esatti: {corr} ({acc:.2f}%)")
        print(f"   • Bilancio Flat (1U): {profit:+.2f}u (ROI: {roi:+.2f}%)")

    print("\n" + "-"*50)
    g_acc = (global_corr / global_tot) * 100 if global_tot > 0 else 0
    print(f"   • Totale generale: {global_corr}/{global_tot} esatti ({g_acc:.2f}%)")
    print("="*50)

if __name__ == "__main__":
    run_backtest()