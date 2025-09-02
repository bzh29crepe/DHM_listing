import pandas as pd
import streamlit as st

df = pd.read_csv("DHMLISTING Complet.csv", encoding="latin1", sep=";")

pb = ("B", "P", "BH", "B &")

df = df[df["Location"].isin(pb)].reset_index()

st.set_page_config(page_title="DHM LISTING", layout="wide")

st.title("DHM LISTING")

st.sidebar.header("Filter Options")

# Filter by 'DHM' column
dhm_filter = st.sidebar.multiselect(
    "Select DHM",
    options=df["Label"].unique()
)

selection = df[df["Label"].isin(dhm_filter)] if dhm_filter else df

if len(dhm_filter) > 0:
    st.dataframe(selection)

print("hello")