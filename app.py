import pandas as pd
import streamlit as st
import os
from PIL import Image
import io

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
                        st.markdown("---")
        else:
            st.info("No items match the selected DHM and location filters.")
    else:
        st.info("Please select at least one DHM to display results.")

elif page == "Table view":
    st.subheader("Full DHM Table with Filters")

    # Keep original Photo column intact
    df_present = df.drop(columns=["Extension"]).copy()

    # Add a temporary column for display
    def check_photo(row):
        possible_extensions = [".jpg", ".png", ".HEIC", ".jpeg"]
        for ext in possible_extensions:
            img_path = f"DHMparis/{row['Photo']}{ext}"
            if os.path.exists(img_path):
                return "Existing"
        return "No pictures"

    df_present["Photo status"] = df_present.apply(check_photo, axis=1)

    filtered_df = df_present.copy()

    # Filters for each column
    for col in df_present.columns:
        if df_present[col].dtype == "object":
            selected_vals = st.sidebar.multiselect(f"Filter {col}", options=df_present[col].dropna().unique(), key=col)
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
        else:
            min_val = df_present[col].min()
            max_val = df_present[col].max()
            selected_range = st.sidebar.slider(f"Filter {col}", min_value=min_val, max_value=max_val,
                                               value=(min_val, max_val), key=col+"_slider")
            filtered_df = filtered_df[(filtered_df[col] >= selected_range[0]) & (filtered_df[col] <= selected_range[1])]

    # --- Editable table ---
    editable_cols = ["Size", "Date", "Location", "Color"]  # only these columns editable
    col_config = {col: {"editable": col in editable_cols} for col in filtered_df.columns}

    edited_df = st.data_editor(
        filtered_df,
        num_rows="fixed",
        use_container_width=True,
        column_config=col_config,
        key="editable_table"
    )

    st.markdown(f"**Total items:** {len(edited_df)}")

    # --- CSV Save button ---
    if st.button("Save changes to CSV"):
        df.update(edited_df[editable_cols])
        df.to_csv("DHMLISTING.csv", sep=";", index=False, encoding="latin1")
        st.success("Changes saved successfully!")

    # --- Download button for selection ---
    download_cols = ["Label", "Size", "Date"]
    if not filtered_df.empty:
        to_download = filtered_df[download_cols]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            to_download.to_excel(writer, index=False, sheet_name="Selection")
        buffer.seek(0)

        st.download_button(
            label="📥 Download the selection",
            data=buffer,
            file_name="DHM_selection.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- Drag and drop image upload ---
    st.markdown("---")
    st.subheader("Upload DHM Image")

    uploaded_file = st.file_uploader(
        "Drag and drop an image here",
        type=["jpg", "png", "jpeg", "HEIC"],
        key="image_uploader"
    )

    # Only show DHMs without an existing picture
    dhm_no_picture = df_present[df_present["Photo status"] == "No pictures"]["Label"].unique()

    if len(dhm_no_picture) > 0:
        dhm_for_image = st.selectbox(
            "Select DHM to associate with this image",
            options=dhm_no_picture,
            key="dhm_selectbox"
        )
    else:
        dhm_for_image = None
        st.info("✅ All DHMs already have pictures. Nothing to upload.")

    # Upload button
    if uploaded_file is not None and dhm_for_image:
        if st.button("Upload image"):
            # Determine original filename from CSV
            photo_name = df.loc[df["Label"] == dhm_for_image, "Photo"].values[0]
            # Get the file extension from uploaded file
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            # Build save path
            save_path = os.path.join("DHMparis", f"{photo_name}{file_ext}")
            # Save the uploaded image
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # ✅ Update extension in CSV if not HEIC
            if file_ext != ".heic":
                df.loc[df["Label"] == dhm_for_image, "Extension"] = file_ext
                df.to_csv("DHMLISTING.csv", sep=";", index=False, encoding="latin1")

            st.success(f"📷 Image saved for DHM {dhm_for_image} at {save_path}")
