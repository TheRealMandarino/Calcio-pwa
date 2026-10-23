import json
import pandas as pd
import numpy as np
from models import probabilita_poisson, correzione_dixon_coles, estrai_esiti_1x2, applica_fattori_correttivi

def esegui_pronostici():
    print("Caricamento dati da partite.json...")
    try:
        with open('partite.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Errore: Il file partite.json non è stato trovato. Esegui prima update_data.py!")
        return

    df = pd.DataFrame(data)
    
    # Conversione gol in numerico
    df['squadra_casa_gol'] = pd.to_numeric(df['squadra_casa_gol'], errors='coerce')
    df['squadra_ospite_gol'] = pd.to_numeric(df['squadra_ospite_gol'], errors='coerce')

    # 1. Partite giocate (per calcolare le forze)
    df_giocate = df.dropna(subset=['squadra_casa_gol', 'squadra_ospite_gol']).copy()
    
    if len(df_giocate) == 0:
        print("Nessuna partita giocata trovata nello storico.")
        return

    media_gol_casa_tot = df_giocate['squadra_casa_gol'].mean()
    media_gol_ospite_tot = df_giocate['squadra_ospite_gol'].mean()

    print(f"\nAnalisi storico completata: {len(df_giocate)} match analizzati.")
    print(f"Media gol campionato - Casa: {media_gol_casa_tot:.2f} | Trasferta: {media_gol_ospite_tot:.2f}\n")

    # Calcoliamo le metriche di attacco e difesa per ogni squadra
    squadre = pd.unique(df_giocate[['squadra_casa', 'squadra_ospite']].values.ravel())
    forze = {}

    for sq in squadre:
        c_giocate = df_giocate[df_giocate['squadra_casa'] == sq]
        fatti_c = c_giocate['squadra_casa_gol'].mean() if len(c_giocate) > 0 else media_gol_casa_tot
        subiti_c = c_giocate['squadra_ospite_gol'].mean() if len(c_giocate) > 0 else media_gol_ospite_tot
        
        t_giocate = df_giocate[df_giocate['squadra_ospite'] == sq]
        fatti_t = t_giocate['squadra_ospite_gol'].mean() if len(t_giocate) > 0 else media_gol_ospite_tot
        subiti_t = t_giocate['squadra_casa_gol'].mean() if len(t_giocate) > 0 else media_gol_casa_tot

        forze[sq] = {
            'attacco_casa': fatti_c / media_gol_casa_tot,
            'difesa_casa': subiti_c / media_gol_ospite_tot,
            'attacco_trasferta': fatti_t / media_gol_ospite_tot,
            'difesa_trasferta': subiti_t / media_gol_casa_tot
        }

    # 2. Partite future da pronosticare (dove i gol sono NaN/None)
    df_future = df[df['squadra_casa_gol'].isna() & df['squadra_ospite_gol'].isna()].copy()
    
    if len(df_future) == 0:
        print("Nessuna partita futura trovata nel calendario corrente.")
        return

    print(f"Trovate {len(df_future)} partite future in calendario. Pronostici per le prime 5 (con gestione Fatica e Boost):\n")
    print("=" * 65)

    count = 0
    for idx, row in df_future.iterrows():
        if count >= 5:
            break
            
        c = row['squadra_casa']
        o = row['squadra_ospite']
        data = row['data']

        if c not in forze or o not in forze:
            continue

        # Lambda base da storico
        lam_c = forze[c]['attacco_casa'] * forze[o]['difesa_trasferta'] * media_gol_casa_tot
        lam_o = forze[o]['attacco_trasferta'] * forze[c]['difesa_casa'] * media_gol_ospite_tot

        # --- SELETTORE FATICA E BOOST PERSONALIZZABILE ---
        # Puoi modificare questi valori al volo in base agli impegni o alla classifica
        fatica_casa = 1.0     # 1.0 = riposo standard (es. 0.92 per impegni ravvicinati)
        fatica_ospite = 1.0   
        boost_casa = 1.0      # 1.0 = standard (es. 1.10 per must-win / obbligo di vittoria)
        boost_ospite = 1.0

        # Applichiamo i fattori correttivi
        lam_c_fin, lam_o_fin = applica_fattori_correttivi(lam_c, lam_o, fatica_casa, fatica_ospite, boost_casa, boost_ospite)

        # Poisson & Dixon-Coles
        matrice = probabilita_poisson(lam_c_fin, lam_o_fin)
        matrice_corretta = correzione_dixon_coles(matrice, lam_c_fin, lam_o_fin)
        esiti = estrai_esiti_1x2(matrice_corretta)

        print(f"Data: {data} | {c} vs {o}")
        print(f"  Lambda effettivi -> Casa: {lam_c_fin:.2f} | Ospite: {lam_o_fin:.2f}")
        print(f"  -> 1 (Casa): {esiti['1']}%  |  X (Pareggio): {esiti['X']}%  |  2 (Ospite): {esiti['2']}%")
        print("-" * 65)
        count += 1

if __name__ == "__main__":
    esegui_pronostici()