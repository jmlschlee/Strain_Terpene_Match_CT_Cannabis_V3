
import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    df_strains = pd.read_csv("final_health_strain_dataset.csv")
    df_mental = pd.read_csv("Mental_Health_Conditions_and_Terpene_Effects.csv")
    df_physical = pd.read_csv("Expanded_Condition-Terpene_Mapping_with_Confidence_Levels.csv")
    return df_strains, df_mental, df_physical

def match_conditions(conditions, df_mental, df_physical):
    terpene_scores = {}
    condition_sources = []

    for cond in conditions:
        mental_hits = df_mental[df_mental['Condition'].str.contains(cond, case=False, na=False)]
        physical_hits = df_physical[df_physical['Condition'].str.contains(cond, case=False, na=False)]

        for _, row in mental_hits.iterrows():
            terp = row['Terpene']
            score = row.get('Confidence', 1)
            terpene_scores[terp] = terpene_scores.get(terp, 0) + score
            condition_sources.append((cond, terp, score))

        for _, row in physical_hits.iterrows():
            terp = row['Terpene']
            score = row.get('Confidence Level', 1)
            terpene_scores[terp] = terpene_scores.get(terp, 0) + score
            condition_sources.append((cond, terp, score))

    return terpene_scores, condition_sources

def score_strains(df_strains, terpene_scores):
    strain_scores = []

    for i, row in df_strains.iterrows():
        score = 0
        details = []
        for terp, weight in terpene_scores.items():
            for col in df_strains.columns:
                if col.lower().startswith(terp.lower()[:4]) and pd.notna(row[col]):
                    amount = row[col]
                    match_score = amount * weight
                    score += match_score
                    details.append(f"{terp} ({amount}×{weight})")
                    break
        strain_scores.append((row['Strain'], score, details))

    strain_scores = sorted(strain_scores, key=lambda x: x[1], reverse=True)
    return strain_scores

# --- UI ---
st.title("CT Cannabis Health Strain Matcher")

df_strains, df_mental, df_physical = load_data()

tab1, tab2 = st.tabs(["Match by Health Condition", "Reverse Lookup by Strain"])

with tab1:
    user_input = st.text_input("Enter 1-5 conditions (mental or physical), separated by commas:")
    if user_input:
        conditions = [c.strip() for c in user_input.split(",")][:5]
        terpene_scores, logic = match_conditions(conditions, df_mental, df_physical)
        ranked_strains = score_strains(df_strains, terpene_scores)

        if ranked_strains:
            st.subheader("Top Strain Matches:")
            for strain, score, reasons in ranked_strains[:10]:
                st.markdown(f"**{strain}** – Score: {score:.2f}")
                st.caption("Logic: " + "; ".join(reasons))

            st.subheader("Strains to Avoid (Low or Conflicting Matches):")
            for strain, score, reasons in ranked_strains[-5:]:
                st.markdown(f"- {strain} (Score: {score:.2f})")

        with st.expander("How this works"):
            st.write("Strains are scored by summing weighted terpene matches from condition-terpene confidence levels.")

with tab2:
    strain_input = st.text_input("Enter strain name for reverse health match:")
    if strain_input:
        strain_row = df_strains[df_strains["Strain"].str.contains(strain_input.strip().lower(), na=False)]
        if not strain_row.empty:
            terpene_present = {col: strain_row.iloc[0][col] for col in df_strains.columns if col.upper() == col and pd.notna(strain_row.iloc[0][col])}
            effects = []
            for terp, amt in terpene_present.items():
                mental_match = df_mental[df_mental['Terpene'].str.contains(terp, case=False, na=False)]
                phys_match = df_physical[df_physical['Terpene'].str.contains(terp, case=False, na=False)]

                for _, row in pd.concat([mental_match, phys_match]).iterrows():
                    effects.append((row['Condition'], terp, row.get('Confidence') or row.get('Confidence Level', 1)))

            st.subheader("Potential Condition Matches:")
            for condition, terp, conf in effects:
                st.markdown(f"- **{condition}** (via {terp}, confidence {conf})")
        else:
            st.warning("Strain not found in dataset.")
