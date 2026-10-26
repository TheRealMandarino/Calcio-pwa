import sqlite3
import pandas as pd
import numpy as np

def compute_team_stats(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM matches WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL", conn)
    conn.close()
    
    if df.empty:
        print("ATTENZIONE: Nessuna partita completata trovata nel database!")
        return {}, {}, {}, {}, 1.0, 1.0

    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    max_date = df['date_dt'].max()
    df['days_ago'] = (max_date - df['date_dt']).dt.days.fillna(0)
    df['weight'] = np.exp(-0.23 * (df['days_ago'] / 365.25))
    
    # Medie gol calcolate per singola lega
    league_avg_home = {}
    league_avg_away = {}
    for league, group in df.groupby('league'):
        w = group['weight']
        total_w = w.sum()
        if total_w > 0:
            league_avg_home[league] = float(np.average(group['home_goals'], weights=w))
            league_avg_away[league] = float(np.average(group['away_goals'], weights=w))
        else:
            league_avg_home[league] = float(group['home_goals'].mean())
            league_avg_away[league] = float(group['away_goals'].mean())

    global_avg_home = float(df['home_goals'].mean())
    global_avg_away = float(df['away_goals'].mean())

    attack_strength = {}
    defense_strength = {}

    for league, l_group in df.groupby('league'):
        l_avg_h = league_avg_home.get(league, global_avg_home)
        l_avg_a = league_avg_away.get(league, global_avg_away)
        l_avg_scored_home = l_avg_h if l_avg_h > 0 else 1.0
        l_avg_conceded_away = l_avg_a if l_avg_a > 0 else 1.0

        h_stats = []
        for team, group in l_group.groupby('home_team'):
            w = group['weight']
            total_w = w.sum()
            scored = np.average(group['home_goals'], weights=w) * total_w if total_w > 0 else 0
            conceded = np.average(group['away_goals'], weights=w) * total_w if total_w > 0 else 0
            h_stats.append({'team': team, 'matches': total_w, 'scored': scored, 'conceded': conceded})
        df_h = pd.DataFrame(h_stats)

        a_stats = []
        for team, group in l_group.groupby('away_team'):
            w = group['weight']
            total_w = w.sum()
            scored = np.average(group['away_goals'], weights=w) * total_w if total_w > 0 else 0
            conceded = np.average(group['home_goals'], weights=w) * total_w if total_w > 0 else 0
            a_stats.append({'team': team, 'matches': total_w, 'scored': scored, 'conceded': conceded})
        df_a = pd.DataFrame(a_stats)

        if not df_h.empty and not df_a.empty:
            teams = pd.merge(df_h, df_a, on='team', suffixes=('_home', '_away'), how='outer').fillna(0)
            teams['total_matches'] = teams['matches_home'] + teams['matches_away']
            teams['total_scored'] = teams['scored_home'] + teams['scored_away']
            teams['total_conceded'] = teams['conceded_home'] + teams['conceded_away']

            for _, row in teams.iterrows():
                team = row['team']
                t_matches = row['total_matches']
                att_rate = (row['total_scored'] / t_matches) if t_matches > 0 else l_avg_scored_home
                def_rate = (row['total_conceded'] / t_matches) if t_matches > 0 else l_avg_conceded_away

                attack_strength[team] = att_rate / l_avg_scored_home if l_avg_scored_home > 0 else 1.0
                defense_strength[team] = def_rate / l_avg_conceded_away if l_avg_conceded_away > 0 else 1.0

    return attack_strength, defense_strength, league_avg_home, league_avg_away, global_avg_home, global_avg_away