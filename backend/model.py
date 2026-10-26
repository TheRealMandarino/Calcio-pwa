import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import poisson
from backend.stats import compute_team_stats

def DixonColes_adjustment(x, y, lambda_h, lambda_a, rho):
    if x == 0 and y == 0:
        return 1.0 - (lambda_h * lambda_a * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_h * rho)
    elif x == 1 and y == 0:
        return 1.0 + (lambda_a * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

def get_h2h_factor(home_team, away_team, db_path="data/database.db"):
    """Calcola un fattore H2H fortemente smorzato e blindato tra 0.95 e 1.05."""
    try:
        conn = sqlite3.connect(db_path)
        query = """
            SELECT home_team, away_team, home_goals, away_goals 
            FROM matches 
            WHERE ((home_team = ? AND away_team = ?) 
               OR (home_team = ? AND away_team = ?))
            AND home_goals IS NOT NULL AND away_goals IS NOT NULL
        """
        df = pd.read_sql(query, conn, params=(home_team, away_team, away_team, home_team))
        conn.close()
        
        if len(df) < 2:
            return 1.0, 1.0
        
        home_scored, away_scored = 0, 0
        total = len(df)
        
        for _, row in df.iterrows():
            if row['home_team'] == home_team:
                home_scored += row['home_goals']
                away_scored += row['away_goals']
            else:
                home_scored += row['away_goals']
                away_scored += row['home_goals']
        
        avg_h = home_scored / total
        avg_a = away_scored / total
        
        h2h_h = 1.0 + ((avg_h - 1.3) * 0.03)
        h2h_a = 1.0 + ((avg_a - 1.1) * 0.03)
        
        h2h_h = max(0.95, min(1.05, h2h_h))
        h2h_a = max(0.95, min(1.05, h2h_a))
        
        return h2h_h, h2h_a
    except Exception:
        return 1.0, 1.0

def calculate_match_probabilities(home_team, away_team, league=None):
    attack, defense, league_avg_h, league_avg_a, global_avg_h, global_avg_a = compute_team_stats()
    
    if league and league in league_avg_h:
        avg_h = league_avg_h[league]
        avg_a = league_avg_a[league]
    else:
        avg_h = global_avg_h
        avg_a = global_avg_a

    att_h = attack.get(home_team, 1.0)
    def_h = defense.get(home_team, 1.0)
    att_a = attack.get(away_team, 1.0)
    def_a = defense.get(away_team, 1.0)

    # Parametri adattivi specifici per lega
    if league == "GER-Bundesliga":
        home_advantage = 1.02  # Fattore campo ridotto per minor pressione ambientale
        rho = -0.05            # Correzione Dixon-Coles più blanda per alti flussi di gol
        max_goals = 9          # Matrice estesa fino a 9 gol per coprire le goleade
    else:
        home_advantage = 1.04  # Standard per Serie A, Premier, Liga, Ligue 1
        rho = -0.11            # Standard Dixon-Coles
        max_goals = 7          # Standard matrice

    # H2H factor
    h2h_h, h2h_a = get_h2h_factor(home_team, away_team)

    lambda_home = max(att_h * def_a * avg_h * home_advantage * h2h_h, 0.70)
    lambda_away = max(att_a * def_h * avg_a * h2h_a, 0.65)

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
        prob_1 /= total
        prob_X /= total
        prob_2 /= total
    else:
        prob_1, prob_X, prob_2 = 0.33, 0.34, 0.33

    return {
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "prob_1": float(prob_1),
        "prob_X": float(prob_X),
        "prob_2": float(prob_2)
    }