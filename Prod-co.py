import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
import os

def simulate_bess(df, battery_mw, battery_mwh, max_cycles_per_day, max_charge_mw, max_discharge_mw):
    df = df.copy()
    df["BESS_Charge"] = 0.0
    df["BESS_Discharge"] = 0.0
    df["Grid_Produktion"] = df["Produktion"]  # Original produktion
    
    battery_soc = 0  # State of Charge (MWh)
    cycles_used = 0
    
    for idx, row in df.iterrows():
        production = row["Produktion"]
        charge_available = min(max_charge_mw, battery_mw, (battery_mwh - battery_soc) * 2)  # Begränsningar
        discharge_available = min(max_discharge_mw, battery_mw, battery_soc * 2)
        
        # Strategi: Ladda när produktion > anslutningskapacitet
        if production > max_charge_mw and cycles_used < max_cycles_per_day:
            charge_amount = min(production - max_charge_mw, charge_available)
            df.at[idx, "BESS_Charge"] = charge_amount
            battery_soc += charge_amount * 0.5  # Anta 0.5h laddning/timme
            cycles_used += charge_amount / battery_mwh
        
        # Ladda ur när produktion < förbrukning
        elif production < max_discharge_mw and battery_soc > 0:
            discharge_amount = min(max_discharge_mw - production, discharge_available)
            df.at[idx, "BESS_Discharge"] = discharge_amount
            battery_soc -= discharge_amount * 0.5
            cycles_used += discharge_amount / battery_mwh
        
        df.at[idx, "Grid_Produktion"] = production - df.at[idx, "BESS_Charge"] + df.at[idx, "BESS_Discharge"]
    
    return df

def main():
    st.title("⚡ BESS Simulator för Vindkraft")
    st.markdown("Simulera hur ett batteri kan optimera vindkraftproduktionen.")
    
    # Sökväg till Excel-filen (ändra till din fil!)
    excel_path = "produktions-data.xlsx"  # Eller full sökväg: "C:/mapp/produktions-data.xlsx"
    
    if not os.path.exists(excel_path):
        st.error(f"Filen '{excel_path}' hittades inte. Kontrollera sökvägen.")
        return
    
    # Läs in Excel-filen
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        st.error(f"Kunde inte läsa Excel-filen: {e}")
        return
    
    # Kontrollera kolumner
    if "Timestamp" not in df.columns or "Produktion" not in df.columns:
        st.error("Excel-filen måste innehålla kolumnerna 'Timestamp' och 'Produktion'.")
        return
    
    # Konvertera Timestamp till datetime
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%Y-%m-%d %H")
    df.set_index("Timestamp", inplace=True)
    
    # Input parametrar
    st.sidebar.header("BESS-inställningar")
    battery_mw = st.sidebar.number_input("Batteri effekt (MW)", min_value=1, value=10)
    battery_mwh = st.sidebar.number_input("Batteri kapacitet (MWh)", min_value=1, value=20)
    max_cycles_per_day = st.sidebar.number_input("Max cykler per dag", min_value=1, value=2)
    max_charge_mw = st.sidebar.number_input("Max laddning (MW)", min_value=1, value=5)
    max_discharge_mw = st.sidebar.number_input("Max urladdning (MW)", min_value=1, value=5)
    
    # Kör simulering
    result_df = simulate_bess(df, battery_mw, battery_mwh, max_cycles_per_day, max_charge_mw, max_discharge_mw)
    
    # Visualisera
    st.subheader("Resultat över tid")
    fig = px.line(result_df, x=result_df.index, y=["Produktion", "Grid_Produktion"],
                 labels={"value": "Effekt (MW)", "variable": "Typ"},
                 title="Vindproduktion med och utan BESS")
    st.plotly_chart(fig)
    
    # Visa batterianvändning
    st.subheader("Batteriaktivitet")
    fig2 = px.area(result_df, x=result_df.index, y=["BESS_Charge", "BESS_Discharge"],
                  labels={"value": "Effekt (MW)", "variable": "BESS"},
                  title="Laddning/Urladdning per timme")
    st.plotly_chart(fig2)
    
    # Sammanfattning
    total_shifted = (result_df["BESS_Charge"].sum() - result_df["BESS_Discharge"].sum())
    st.metric("Total produktion flyttad (MWh)", round(total_shifted, 2))

if __name__ == "__main__":
    main()