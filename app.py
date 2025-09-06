import pandas as pd
import streamlit as st
import os
from PIL import Image

# Try to support HEIC images
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    heic_supported = True
except ImportError:
    heic_supported = False

# Load CSV
df = pd.read_csv("DHMLISTING.csv", encoding="latin1", sep=";")

st.set_page_config(page_title="DHM LISTING", layout="wide")
st.title("DHM LISTING")

# --- PAGE SELECTION ---
page = st.sidebar.radio("Select Page", ["Gallery view", "Table view"])

if page == "Gallery view":
    st.sidebar.header("Filter Options")
    # Sidebar filter by 'Location' (optional)
    location_filter = st.sidebar.multiselect(
        "Refine by Location",
        options=df["Location"].dropna().unique()
    )

    # Filter DHM options based on selected locations
    if location_filter:
        dhm_options = df[df["Location"].isin(location_filter)]["Label"].unique()
    else:
        dhm_options = df["Label"].unique()

    # Sidebar filter by 'Label' (mandatory)
    dhm_filter = st.sidebar.multiselect(
        "Select DHM",
        options=dhm_options
    )

    if dhm_filter:
        selection = df[df["Label"].isin(dhm_filter)]
        if location_filter:
            selection = selection[selection["Location"].isin(location_filter)]

        if not selection.empty:
            st.subheader("Selected Variation")

            if not heic_supported:
                st.warning("⚠️ .HEIC images may not display because 'pillow-heif' is not installed. "
                           "Install it with: `pip install pillow-heif`")

            for _, row in selection.iterrows():
                img_path = f"DHMparis/{row['Photo']}{row['Extension']}"
                col1, col2 = st.columns([2, 1])
                if os.path.exists(img_path):
                    try:
                        image = Image.open(img_path)
                        with col1:
                            st.image(image, use_column_width=True)
                        with col2:
                            st.markdown(f"""
                            ## DHM {row['Label']}
                            ### {row['Size'] if pd.notna(row['Size']) else 'Unknown size'} cm
                            {row['Date'] if pd.notna(row['Date']) else 'Unknown date'} 

                            **Location:** {row['Location'] if pd.notna(row['Location']) else 'Unknown location'}
                            """)
                        st.markdown("---")
                    except Exception as e:
                        st.error(f"Could not load image for DHM {row['Label']}: {e}")
                else:
                    with col1:
                        st.title(f"No image found for DHM {row['Label']}")
                    with col2:
                        st.markdown(f"""
                        ## DHM {row['Label']}
                        ### {row['Size'] if pd.notna(row['Size']) else 'Unknown size'} cm
                        {row['Date'] if pd.notna(row['Date']) else 'Unknown date'} 

                        **Location:** {row['Location'] if pd.notna(row['Location']) else 'Unknown location'}
                        """)
        else:
            st.info("No items match the selected DHM and location filters.")
    else:
        st.info("Please select at least one DHM to display results.")

elif page == "Table view":
    st.subheader("Full DHM Table with Filters")
    df_present = df.drop(columns=["Photo", "Extension"])
    filtered_df = df_present.copy()
    # Create a filter for each column
    for col in df_present.columns:
        if df_present[col].dtype == "object":
            selected_vals = st.sidebar.multiselect(f"Filter {col}", options=df_present[col].dropna().unique(), key=col)
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
        else:
            min_val = df_present[col].min()
            max_val = df_present[col].max()
            selected_range = st.sidebar.slider(f"Filter {col}", min_value=min_val, max_value=max_val, value=(min_val, max_val), key=col+"_slider")
            filtered_df = filtered_df[(filtered_df[col] >= selected_range[0]) & (filtered_df[col] <= selected_range[1])]

    st.dataframe(filtered_df.reset_index(drop=True))
    st.markdown(f"**Total items:** {len(filtered_df)}")