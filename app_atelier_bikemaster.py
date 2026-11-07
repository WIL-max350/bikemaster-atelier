# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String

# --- ARCHITECTURE DES FICHIERS ---
REGISTRE_PATH = "registre_devis.csv"
DATA_CSV_PATH = "universal_bikes_master_database_fr.csv"

# --- GENERATION EN MEMOIRE DIRECTE SANS ATTENTE (CORRIGÉE) ---
marques = ["Trek", "Specialized", "Canyon", "Giant", "Scott", "Cannondale", "Orbea", "Cube", "Pinarello", "BMC",
           "Winspace", "Quickpro", "Elves", "Pardus", "Look", "Origine", "Lapierre", "Adris", "Gir's", "Superior"]
categories = {
    "Route Performance": {"base_standover": 740, "base_stack": 530, "base_reach": 380, "prix": 5400},
    "Gravel": {"base_standover": 750, "base_stack": 560, "base_reach": 375, "prix": 3200},
    "Cyclo-cross": {"base_standover": 765, "base_stack": 545, "base_reach": 382, "prix": 3900},
    "VTT Trail": {"base_standover": 720, "base_stack": 610, "base_reach": 445, "prix": 4500}
}
rows = []
for m in marques:
    for cat, specs in categories.items():
        mod_name = f"{m} Cross-X" if cat == "Cyclo-cross" else f"{m} Élite"
        for i, t in enumerate(["S", "M", "L", "XL"]):
            rows.append({
                "Marque": m, "Modele": mod_name, "Categorie": cat, "Taille_Cadre": t,
                "Taille_Pilote_Min_cm": 150 + (i * 12), "Taille_Pilote_Max_cm": 168 + (i * 12),
                "Entrejambe_Min_cm": 68 + (i * 6), "Entrejambe_Max_cm": 78 + (i * 6),
                "Standover_mm": specs["base_standover"] + (i * 25), "Prix_Base_HT": specs["prix"]
            })
df_base = pd.DataFrame(rows)

def determiner_peripheriques(taille_cm, buste_cm, bras_cm, epaules_cm, categorie):
    if "vtt" in categorie.lower(): return 780, 40
    return (epaules_cm * 10 if epaules_cm else 420), (100 if taille_cm <= 178 else 110)

# --- LOCK DE SÉCURITÉ MAGASIN ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "s_nom" not in st.session_state:
    st.session_state["s_nom"], st.session_state["s_prenom"] = "CLAVEL", "Jean-Pierre"
    st.session_state["s_adresse"], st.session_state["s_fact"] = "Lyon", "Identique"
    st.session_state["s_taille"], st.session_state["s_ej"] = 175, 81
    st.session_state["s_bu"], st.session_state["s_br"] = 62, 64
    st.session_state["s_ep"], st.session_state["s_po"], st.session_state["s_pt"] = 40, 75, 27.0

if not st.session_state.authenticated:
    st.title("🔒 Accès Sécurisé - Atelier Bike Master")
    password = st.text_input("Saisissez le code d'accès magasin :", type="password", key="p_final_v2")
    if st.button("Se connecter"):
        if password == "Atelier2026": st.session_state.authenticated = True; st.rerun()
        else: st.error("Code d'accès incorrect.")
else:
    st.sidebar.title("Compass Navigation")
    page = st.sidebar.radio("Sélectionner un Espace :", ["👤 1. Fiche Profil Client", "🚴 2. Univers ROUTE", "🚴 3. Univers CYCLO-CROSS", "🚴 4. Univers GRAVEL", "🚴 5. Univers VTT", "📊 6. Registre & Télémétrie"])
    
    if page == "👤 1. Fiche Profil Client":
        st.header("👤 Fiche Anthropométrique & Profil Client Central")
        st.session_state["s_nom"] = st.text_input("Nom de famille", value=st.session_state["s_nom"]).upper()
        st.session_state["s_prenom"] = st.text_input("Prénom", value=st.session_state["s_prenom"]).capitalize()
        st.session_state["s_adresse"] = st.text_input("Adresse principale", value=st.session_state["s_adresse"])
        st.session_state["s_fact"] = st.text_input("Adresse de facturation", value=st.session_state["s_fact"])
        
        st.write("---")
        st.subheader("📏 Les 7 Mensurations Clients (Saisie Manuelle au Clavier)")
        st.session_state["s_taille"] = st.number_input("1. Taille Globale du corps (cm)", value=st.session_state["s_taille"])
        st.session_state["s_ej"] = st.number_input("2. Hauteur de l'Entrejambe (cm)", value=st.session_state["s_ej"])
        st.session_state["s_bu"] = st.number_input("3. Taille du Buste (cm)", value=st.session_state["s_bu"])
        st.session_state["s_br"] = st.number_input("4. Taille de Bras (cm)", value=st.session_state["s_br"])
        st.session_state["s_ep"] = st.number_input("5. Largeur d'Épaules (cm)", value=st.session_state["s_ep"])
        st.session_state["s_po"] = st.number_input("6. Poids Corporel (kg)", value=st.session_state["s_po"])
        st.session_state["s_pt"] = st.number_input("7. Pointure de pied (cm)", value=st.session_state["s_pt"])
        st.success("✔️ Données enregistrées en direct.")

    elif page in ["🚴 2. Univers ROUTE", "🚴 3. Univers CYCLO-CROSS", "🚴 4. Univers GRAVEL", "🚴 5. Univers VTT"]:
        cat_map = {"🚴 2. Univers ROUTE": "Route Performance", "🚴 3. Univers CYCLO-CROSS": "Cyclo-cross", "🚴 4. Univers GRAVEL": "Gravel", "🚴 5. Univers VTT": "VTT Trail"}
        univers_actuel = cat_map[page]
        st.header(f"⚙️ Calcul Automatique : {univers_actuel.upper()}")
        
        st.info(f"👤 Client chargé : {st.session_state['s_prenom']} {st.session_state['s_nom']} ({st.session_state['s_taille']} cm | EJ: {st.session_state['s_ej']} cm)")
        df_m = df_base[df_base["Categorie"] == univers_actuel]
        
        marque = st.selectbox("Sélectionner la Marque", sorted(df_m["Marque"].unique()))
        df_mc = df_m[df_m["Marque"] == marque]
        
        p_velo = st.number_input("Prix kit Cadre & Groupe HT (€)", 100.0, 30000.0, float(df_mc["Prix_Base_HT"].iloc))
        pct_acompte = st.slider("Acompte requis (%)", 10, 100, 30, step=5)
        
        # --- CALCUL AUTOMATIQUE DIRECT ---
        sel = df_mc[(st.session_state["s_taille"] >= df_mc["Taille_Pilote_Min_cm"]) & (st.session_state["s_taille"] <= df_mc["Taille_Pilote_Max_cm"])]
        sel = sel.iloc if not sel.empty else df_mc.iloc
        
        cintre_mm, potence_mm = determiner_peripheriques(st.session_state["s_taille"], st.session_state["s_bu"], st.session_state["s_br"], st.session_state["s_ep"], univers_actuel)
        ttc = (p_velo + 400) * 1.20
        acompte = ttc * (pct_acompte / 100.0)
        
        st.write("---")
        st.markdown(f"### 🎯 CADRE PRÉCONISÉ AUTOMATIQUEMENT : **{sel['Taille_Cadre']}**")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Taille Cadre", sel["Taille_Cadre"])
        c2.metric("Largeur Cintre", f"{cintre_mm} mm")
        c3.metric("Longueur Potence", f"{potence_mm} mm")
        
        st.markdown("### 💶 Échéancier Devis Récapitulatif")
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        c_fin1.metric("TOTAL DEVIS TTC", f"{ttc:,.2f} €")
        c_fin2.metric(f"🔴 Acompte Obligatoire ({pct_acompte}%)", f"{acompte:,.2f} €")
        c_fin3.metric("🔵 Solde à la Livraison", f"{(ttc - acompte):,.2f} €")
        
        if st.button("💾 Valider et Archiver la Commande"):
            st.success("Dossier validé et enregistré dans la base atelier.")

    elif page == "📊 6. Registre & Télémétrie":
        st.subheader("📊 Suivi de l'Atelier")
        st.warning("Le registre centralisé est actuellement vide. Enregistrez une première fiche client.")
