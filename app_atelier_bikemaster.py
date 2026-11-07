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

# --- ARCHITECTURE DU SYSTEME DE FICHIERS ---
os.makedirs("Archives_Clients", exist_ok=True)
REGISTRE_PATH = "registre_devis.csv"
DATA_CSV_PATH = "universal_bikes_master_database_fr.csv"

# --- SYSTEME DE GENERATION AUTOMATIQUE DU CATALOGUE (400 LIGNES) ---
if not os.path.exists(DATA_CSV_PATH):
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
                    "Top_Tube_mm": 520 + (i * 20), "Standover_mm": specs["base_standover"] + (i * 25),
                    "Reach_mm": specs["base_reach"] + (i * 15), "Stack_mm": specs["base_stack"] + (i * 20),
                    "Head_Angle_deg": 71.5 if cat == "Cyclo-cross" else (66.0 if "VTT" in cat else 72.0),
                    "Chainstay_mm": 425 if cat == "Cyclo-cross" else 435, "BB_Drop_mm": 62,
                    "Prix_Base_HT": specs["prix"]
                })
    pd.DataFrame(rows).to_csv(DATA_CSV_PATH, index=False, encoding='utf-8')

@st.cache_data
def charger_base_universelle_reelle():
    return pd.read_csv(DATA_CSV_PATH, encoding='utf-8')

# --- LOGIQUE POSTURALE ET ETUDE TECHNIQUE ---
def normaliser_nom_dossier(nom):
    return re.sub(r'[^A-Z0-9_]', '', nom.upper().replace(" ", "_").replace("-", "_"))

def determiner_peripheriques(taille_cm, buste_cm, bras_cm, epaules_cm, categorie):
    if "vtt" in categorie.lower():
        largeur_cintre = 760 if taille_cm < 170 else (780 if taille_cm <= 180 else 800)
        potence = 40
    else:
        largeur_cintre = epaules_cm * 10 if epaules_cm else (400 if taille_cm <= 178 else 420)
        index_buste_bras = (buste_cm + bras_cm) / 2 if (buste_cm and bras_cm) else 65
        if index_buste_bras < 60: potence = 90
        elif index_buste_bras <= 70: potence = 100
        else: potence = 110
    return largeur_cintre, potence

def inscrire_dans_registre(nom, prenom, h, ej, buste, bras, epaules, marque, modele, cat, taille_c, total_ht, total_ttc, acompte, solde, chemin_pdf):
    nouvelle_ligne = {
        "Date": datetime.now().strftime("%Y-%m-%d"), "Nom": nom.upper(), "Prenom": prenom.capitalize(),
        "Taille_cm": h, "Entrejambe_cm": ej, "Buste_cm": buste, "Bras_cm": bras, "Epaule_cm": epaules,
        "Marque": marque, "Modele": modele, "Categorie": cat, "Taille_Cadre": taille_c,
        "Total_HT": round(total_ht, 2), "Total_TTC": round(total_ttc, 2),
        "Acompte_TTC": round(acompte, 2), "Solde_TTC": round(solde, 2), "Fichier_PDF": chemin_pdf
    }
    df_line = pd.DataFrame([nouvelle_ligne])
    if os.path.exists(REGISTRE_PATH):
        try:
            df_ext = pd.read_csv(REGISTRE_PATH, encoding='utf-8')
            df_final = pd.concat([df_ext, df_line], ignore_index=True)
        except: df_final = df_line
    else: df_final = df_line
    df_final.to_csv(REGISTRE_PATH, index=False, encoding='utf-8')

def generer_pdf_devis(chemin_complet, client, velo_info, cintre, potence, prix, pct):
    doc = SimpleDocTemplate(chemin_complet, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    style_text = ParagraphStyle('Txt', fontSize=9, leading=13)
    style_dr = ParagraphStyle('Dr', parent=style_text, alignment=2)
    logo = Drawing(120, 35)
    logo.add(Rect(0, 0, 120, 35, fillColor=colors.HexColor("#1A365D"), strokeColor=None))
    logo.add(String(12, 12, "BIKE MASTER", fontSize=13, fontName="Helvetica-Bold", fillColor=colors.white))
    
    elements = [
        Table([[logo, Paragraph("<b>BIKE MASTER ATELIER</b><br/>75017 Paris", style_dr)]], colWidths=),
        Spacer(1, 15),
        Table([
            [Paragraph("<b>Émetteur :</b> Bike Master Paris", style_text), Paragraph(f"<b>Client :</b> {client['nom']} {client['prenom']}<br/>{client['adresse']}<br/>Facturation : {client['adresse_fact']}", style_text)],
            [Paragraph(f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y')}", style_text), Paragraph("", style_text)]
        ], colWidths=),
        Spacer(1, 15),
        Paragraph("<b>1. Métrologie Anthropométrique & Cadre Retenu</b>", styles['Heading3']),
        Table([
            ["Marque", "Modèle", "Cadre Recommandé", "Largeur Cintre", "Longueur Potence", "Arbitrage"],
            [velo_info['Marque'], velo_info['Modele'], velo_info['Taille_Cadre'], f"{cintre} mm", f"{potence} mm", velo_info['Profil']]
        ], colWidths=),
        Spacer(1, 15),
        Paragraph("<b>2. Grille Commerciale & Échéancier</b>", styles['Heading3'])
    ]
    ts = TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")), ('PADDING', (0,0), (-1,-1), 5), ('FONTSIZE', (0,0), (-1,-1), 8)])
    elements[-2].setStyle(ts)
    
    lignes = [
        ["Désignation des Équipements", "Qté", "Montant HT"],
        [f"Kit Châssis : {velo_info['Marque']} {velo_info['Modele']}", "1", f"{prix['velo']:.2f} €"],
        ["Poste de Pilotage Sur-Mesure", "1", f"{(prix['cintre'] + prix['potence']):.2f} €"],
        ["Forfait Main d'œuvre Atelier & Posture", "1", f"{prix['mo']:.2f} €"]
    ]
    if prix['remise'] > 0: lignes.append([f"Remise Commerciale Appliquée", "1", f"-{prix['remise']:.2f} €"])
    lignes.extend([
        ["", "Sous-Total Net HT :", f"{prix['net_ht']:.2f} €"], ["", "TVA (20%) :", f"{prix['tva']:.2f} €"],
        ["", "TOTAL COMMANDÉ TTC :", f"{prix['ttc']:.2f} €"], ["", f"ACOMPTE REQUIS ({pct}%) :", f"{prix['acompte']:.2f} €"],
        ["", "SOLDE À LA LIVRAISON :", f"{prix['solde']:.2f} €"]
    ])
    tf = Table(lignes, colWidths=)
    tf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-6), 0.5, colors.HexColor("#E2E8F0")), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('PADDING', (0,0), (-1,-1), 5), ('FONTNAME', (1,-5), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1,-2), (2,-2), colors.HexColor("#C53030")), ('BACKGROUND', (1,-2), (2,-2), colors.HexColor("#FEF2F2")),
        ('TEXTCOLOR', (1,-1), (2,-1), colors.HexColor("#2B6CB0"))
    ]))
    elements.append(tf)
    doc.build(elements)

# --- INITIALISATION ET LOCK SECURITE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# Initialisation forcée de la mémoire permanente pour la fiche client
if "nom" not in st.session_state: st.session_state.nom = "CLAVEL"
if "prenom" not in st.session_state: st.session_state.prenom = "Jean-Pierre"
if "adresse" not in st.session_state: st.session_state.adresse = "45 Rue de la République, Lyon"
if "adresse_fact" not in st.session_state: st.session_state.adresse_fact = "Identique à l'adresse principale"
if "taille" not in st.session_state: st.session_state.taille = 175
if "entrejambe" not in st.session_state: st.session_state.entrejambe = 81
if "buste" not in st.session_state: st.session_state.buste = 62
if "bras" not in st.session_state: st.session_state.bras = 64
if "epaules" not in st.session_state: st.session_state.epaules = 40

if not st.session_state.authenticated:
    st.title("🔒 Accès Sécurisé - Atelier Bike Master")
    password = st.text_input("Saisissez le code d'accès magasin :", type="password", key="pass_v8_stable")
    if st.button("Se connecter"):
        if password == "Atelier2026": st.session_state.authenticated = True; st.rerun()
        else: st.error("Code d'accès incorrect.")
else:
    df_base = charger_base_universelle_reelle()
    st.sidebar.title("🧭 Navigation Magasin")
    
    page = st.sidebar.radio("Sélectionner un Espace :", [
        "👤 1. Fiche Profil Client", 
        "🚴 2. Univers ROUTE", 
        "🚴 3. Univers CYCLO-CROSS", 
        "🚴 4. Univers GRAVEL", 
        "🚴 5. Univers VTT", 
        "📊 6. Registre & Télémétrie"
    ])
    
    # --- ESPACE 1 : FICHE PROFIL CLIENT (SAUVEGARDE EN TEMPS RÉEL) ---
    if page == "👤 1. Fiche Profil Client":
        st.header("👤 Fiche Anthropométrique & Profil Client Central")
        st.write("Saisissez ici l'identité complète et les mensurations. Tout changement est sauvegardé automatiquement.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.nom = st.text_input("Nom de famille", value=st.session_state.nom).upper()
            st.session_state.prenom = st.text_input("Prénom", value=st.session_state.prenom).capitalize()
            st.session_state.adresse = st.text_input("Adresse principale", value=st.session_state.adresse)
