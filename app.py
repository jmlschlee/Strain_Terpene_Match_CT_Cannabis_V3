
import streamlit as st
import pandas as pd
import difflib

@st.cache_data
def load_data():
    df_strains = pd.read_csv("normalized_strain_registry.csv")
    df_mental = pd.read_csv("Mental_Health_Conditions_and_Terpene_Effects.csv")
    df_physical = pd.read_csv("Expanded_Condition-Terpene_Mapping_with_Confidence_Levels.csv")
    return df_strains, df_mental, df_physical

def unify_terpene_name(terpene, reference_list):
    for ref in reference_list:
        matches = [terpene[i:i+4] for i in range(len(terpene) - 3)]
        if any(m in ref for m in matches):
            return ref
    return terpene

def get_terpene_map(df):
    terp_map = {}
    for _, row in df.iterrows():
        condition = row["Condition"].strip().lower()
        helps = row.get("Helpful_Terpenes", "")
        avoids = row.get("Avoid_Terpenes", "")
        conf = float(row.get("Confidence_Level", 1)) if "Confidence_Level" in row else 1

        for terp in str(helps).split(","):
            terp = terp.strip().lower()
            if terp:
                if condition not in terp_map:
                    terp_map[condition] = []
                terp_map[condition].append((terp, conf))
    return terp_map

def analyze_conditions(input_conditions, df_strains, terp_map):
    terpene_cols = [col.lower() for col in df_strains.columns if col.upper() == col and df_strains[col].dtype != 'O']
    results = []

    for _, row in df_strains.iterrows():
        score = 0
        reasons = []
        avoid_flag = False
        for cond in input_conditions:
            if cond in terp_map:
                for t_raw, conf in terp_map[cond]:
                    terp = unify_terpene_name(t_raw, terpene_cols)
                    amount = row.get(terp.upper(), 0)
                    if amount > 0:
                        score += amount * conf
                        reasons.append(f"✔ {terp.title()} ({amount}) helps with {cond} (confidence {conf})")
                    elif "anxiety" in cond or "panic" in cond:
                        avoid_flag = True
        results.append((row["Strain"], score, reasons, avoid_flag))
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def analyze_strain(strain_name, df_strains, terp_map):
    strain_name = strain_name.lower()
    match = df_strains[df_strains["Strain"].str.contains(strain_name)]
    if match.empty:
        return None, []
    row = match.iloc[0]
    terpene_cols = [col.lower() for col in df_strains.columns if col.upper() == col and df_strains[col].dtype != 'O']
    helpful = []
    harmful = []

    for cond, tlist in terp_map.items():
        for t_raw, conf in tlist:
            terp = unify_terpene_name(t_raw, terpene_cols)
            if row.get(terp.upper(), 0) > 0:
                helpful.append((cond, terp, row.get(terp.upper(), 0), conf))
            elif "anxiety" in cond or "panic" in cond:
                harmful.append((cond, terp))

    return row["Strain"], (helpful, harmful)

# --- Streamlit UI ---
st.title("CT Strain Health Match Finder")

df_strains, df_mental, df_physical = load_data()
terp_map = get_terpene_map(pd.concat([df_mental, df_physical]))

mode = st.radio("Choose Mode", ["Find Strains by Conditions", "Analyze Strain for Effects"])

if mode == "Find Strains by Conditions":
    condition_input = st.text_input("Enter 1–5 conditions (mental or physical), comma-separated").lower()
    input_conditions = [x.strip() for x in condition_input.split(",") if x.strip()]
    if input_conditions:
        results = analyze_conditions(input_conditions, df_strains, terp_map)
        st.subheader("Top 5 Matches")
        for name, score, reasons, _ in results[:5]:
            st.markdown(f"**{name.title()}** – Score: {score:.2f}")
            for r in reasons:
                st.write(r)
            st.markdown("---")
        st.subheader("⚠️ Strains to Avoid")
        for name, _, _, avoid in results:
            if avoid:
                st.write(f"- {name.title()}")

elif mode == "Analyze Strain for Effects":
    strain_query = st.text_input("Enter a strain/product name").strip().lower()
    if strain_query:
        name, (helpful, harmful) = analyze_strain(strain_query, df_strains, terp_map)
        if name:
            st.subheader(f"✅ {name.title()} may help with:")
            for cond, terp, amt, conf in helpful:
                st.write(f"- {cond.title()} (via {terp}, {amt} mg, confidence {conf})")
            st.subheader("⚠️ May worsen:")
            for cond, terp in harmful:
                st.write(f"- {cond.title()} (potential interaction with {terp})")
        else:
            st.warning("No matching strain found.")
