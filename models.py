import numpy as np
from scipy.stats import poisson

def calcola_forze_squadre(df):
    """
    Calcola i parametri di attacco e difesa medi per le squadre basandosi sui dati storici.
    """
    gol_fatti_casa = df['squadra_casa_gol'].mean()
    gol_subiti_casa = df['squadra_ospite_gol'].mean()
    return gol_fatti_casa, gol_subiti_casa

def probabilita_poisson(lambda_casa, lambda_ospite, max_gol=6):
    """
    Calcola la matrice delle probabilità dei risultati esatti con la distribuzione di Poisson.
    """
    matrice_prob = np.outer(
        [poisson.pmf(i, lambda_casa) for i in range(max_gol)],
        [poisson.pmf(j, lambda_ospite) for j in range(max_gol)]
    )
    return matrice_prob

def correzione_dixon_coles(matrice_prob, lambda_c, lambda_o, rho=-0.1):
    """
    Applica la correzione di Dixon-Coles per i punteggi bassi (0-0, 1-0, 0-1, 1-1).
    """
    if matrice_prob.shape[0] > 1 and matrice_prob.shape[1] > 1:
        matrice_prob[0, 0] *= max(0.001, 1 - lambda_c * lambda_o * rho)
        matrice_prob[0, 1] *= max(0.001, 1 + lambda_c * rho)
        matrice_prob[1, 0] *= max(0.001, 1 + lambda_o * rho)
        matrice_prob[1, 1] *= max(0.001, 1 - rho)
        matrice_prob /= np.sum(matrice_prob)
    return matrice_prob

def estrai_esiti_1x2(matrice_prob):
    """
    Estrae le percentuali di vittoria Casa, Pareggio, Vittoria Ospite dalla matrice delle probabilità.
    """
    p_casa = np.sum(np.tril(matrice_prob, -1))
    p_pareggio = np.sum(np.diag(matrice_prob))
    p_ospite = np.sum(np.triu(matrice_prob, 1))
    
    return {
        "1": round(p_casa * 100, 2),
        "X": round(p_pareggio * 100, 2),
        "2": round(p_ospite * 100, 2)
    }
def applica_fattori_correttivi(lambda_c, lambda_o, fattore_fatica_c=1.0, fattore_fatica_o=1.0, boost_c=1.0, boost_o=1.0):
    """
    Modifica i lambda attesi di casa e trasferta applicando:
    - Fattore fatica (es. 0.90 / 0.95 per impegni ravvicinati / infrasettimanali)
    - Fattore boost (es. 1.10 / 1.15 per must-win o reazione psicologica post-crisi)
    """
    lam_c_modificato = lambda_c * fattore_fatica_c * boost_c
    lam_o_modificato = lambda_o * fattore_fatica_o * boost_o
    
    # Evitiamo valori negativi o nulli azzerati
    return max(0.05, lam_c_modificato), max(0.05, lam_o_modificato)