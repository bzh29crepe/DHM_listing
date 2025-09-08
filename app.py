import pandas as pd
import streamlit as st
import os
from PIL import Image
import io
from fpdf import FPDF
import requests
from io import BytesIO

# Try to support HEIC images
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    heic_supported = True
except ImportError:
    heic_supported = False

# --- GitHub raw base paths ---
CSV_URL = "https://raw.githubusercontent.com/bzh29crepe/DHM_listing/main/DHMLISTING.csv"
IMG_BASE = "https://raw.githubusercontent.com/bzh29crepe/DHM_listing/main/DHMparis"

# Load CSV directly from GitHub
df = pd.read_csv(CSV_URL, encoding="latin1", sep=";")

df.columns = df.columns.str.strip()

st.set_page_config(page_title="DHM LISTING", layout="wide")

# --- Initialize session_state for gallery filter ---
if "gallery_filter" not in st.session_state:
    st.session_state["gallery_filter"] = []

st.title("DHM LISTING")

# --- Helper to load image from GitHub ---
def load_image(row):
    url = f"{IMG_BASE}/{row['Photo']}{row['Extension']}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        st.warning(f"Could not load image {row['Variation']} from GitHub: {e}")
        return None

# --- PAGE SELECTION ---
page = st.sidebar.radio("Select Page", ["Gallery view", "Table view"])

if page == "Gallery view":
    st.subheader("Gallery View")

    if st.button("Download PDF"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        selected_df = df[df["Variation"].isin(st.session_state["gallery_filter"])]

        for _, row in selected_df.iterrows():
            img = load_image(row)
            if img is not None:
                try:
                    # Save temporary PNG
                    tmp_path = f"temp_{row['Variation']}.png"
                    img.save(tmp_path, format="PNG")

                    # Add new page
                    pdf.add_page()

                    # --- Calculate max dimensions ---
                    max_page_width_mm = 210 - 20  # A4 width minus margins
                    max_img_height_mm = (297 - 20) * 2/3  # max 2/3 page height
                    img_width_px, img_height_px = img.size
                    img_ratio = img_width_px / img_height_px

                    # Scale to fit width and max height
                    pdf_width_mm = min(max_page_width_mm, img_width_px * 0.264583)
                    pdf_height_mm = pdf_width_mm / img_ratio
                    if pdf_height_mm > max_img_height_mm:
                        pdf_height_mm = max_img_height_mm
                        pdf_width_mm = pdf_height_mm * img_ratio

                    # Image position: center horizontally
                    x_pos = (210 - pdf_width_mm) / 2  # page width is 210 mm
                    y_pos = 20
                    pdf.image(tmp_path, x=x_pos, y=y_pos, w=pdf_width_mm, h=pdf_height_mm)

                    # Add centered text below the image
                    pdf.set_xy(0, y_pos + pdf_height_mm + 5)  # top margin + image height + 5 mm
                    pdf.set_font("Times", "B", 16)
                    pdf.multi_cell(210, 8, f"Variation {row['Variation']}, {row['Date']}", align="C")
                    pdf.set_font("Times", "", 14)
                    size_text = f"{row['Size']} cm" if pd.notna(row['Size']) else "Unknown size"
                    pdf.multi_cell(210, 6, size_text, align="C")

                except Exception as e:
                    st.warning(f"Could not add image {row['Variation']}: {e}")
                    continue

        # Output PDF to BytesIO
        pdf_bytes = pdf.output(dest="S").encode("latin1")
        pdf_buffer = io.BytesIO(pdf_bytes)

        st.download_button(
            label="Download PDF",
            data=pdf_buffer,
            file_name="DHM_gallery.pdf",
            mime="application/pdf"
        )

    st.sidebar.header("Filter Options")
    # Sidebar filter by 'Location' (optional)
    location_filter = st.sidebar.multiselect(
        "Refine by Location",
        options=df["Location"].dropna().unique()
    )

    # Filter DHM options based on selected locations
    if location_filter:
        dhm_options = df[df["Location"].isin(location_filter)]["Variation"].unique()
    else:
        dhm_options = df["Variation"].unique()

    # Sidebar filter by 'Variation' (mandatory)
    if st.session_state["gallery_filter"]:
        dhm_filter = st.sidebar.multiselect(
            "Select DHM",
            options=dhm_options,
            default=st.session_state["gallery_filter"]
        )
    else:
        dhm_filter = st.sidebar.multiselect(
            "Select DHM",
            options=dhm_options,
            default=[]
        )

    if dhm_filter:
        selection = df[df["Variation"].isin(dhm_filter)]
        if location_filter:
            selection = selection[selection["Location"].isin(location_filter)]

        if not selection.empty:
            st.subheader("Selected Variation")

            if not heic_supported:
                st.warning(" .HEIC images may not display because 'pillow-heif' is not installed. "
                           "Install it with: `pip install pillow-heif`")

            for _, row in selection.iterrows():
                image = load_image(row)
                col1, col2 = st.columns([2, 1])
                if image is not None:
                    with col1:
                        st.image(image, use_container_width=True)
                    with col2:
                        st.markdown(f"""
                        ## Variation {row['Variation']}
                        ### {row['Size'] if pd.notna(row['Size']) else 'Unknown size'} cm
                        {row['Date'] if pd.notna(row['Date']) else 'Unknown date'} 

                        **Location:** {row['Location'] if pd.notna(row['Location']) else 'Unknown location'}
                        """)
                    st.markdown("---")
                else:
                    with col1:
                        st.title(f"No image found for DHM {row['Variation']}")
                    with col2:
                        st.markdown(f"""
                        ## DHM {row['Variation']}
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

    # Keep original Photo column intact (no automatic check)
    df_present = df.drop(columns=["Extension"]).copy()

    filtered_df = df_present.copy()

    # Filters for each column
    for col in df_present.columns:
        if df_present[col].dtype == "object":
            selected_vals = st.sidebar.multiselect(
                f"Filter {col}", 
                options=df_present[col].dropna().unique(), 
                key=col
            )
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
        else:
            min_val = df_present[col].min()
            max_val = df_present[col].max()
            selected_range = st.sidebar.slider(
                f"Filter {col}", 
                min_value=min_val, 
                max_value=max_val,
                value=(min_val, max_val), 
                key=col+"_slider"
            )
            filtered_df = filtered_df[
                (filtered_df[col] >= selected_range[0]) & 
                (filtered_df[col] <= selected_range[1])
            ]

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
    download_cols = ["Variation", "Size", "Date"]
    if not filtered_df.empty:
        to_download = filtered_df[download_cols]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            to_download.to_excel(writer, index=False, sheet_name="Selection")
        buffer.seek(0)

        st.download_button(
            label="Download the selection",
            data=buffer,
            file_name="DHM_selection.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- Apply filters in Gallery button ---
    if st.button("Apply the filters in the Gallery"):
        # Save the filtered DHMs in session_state
        st.session_state["gallery_filter"] = filtered_df["Variation"].tolist()
        # Switch to Gallery view
        st.rerun()

    # --- Manual "Check Photo" with dropdown ---
    st.markdown("---")
    st.subheader("Check DHM Photos")

    if not filtered_df.empty:
        dhm_to_check = st.selectbox(
            "Select a DHM to check",
            options=filtered_df["Variation"].unique(),
            key="dhm_check_select"
        )

        if st.button("Check photo"):
            photo_name = df.loc[df["Variation"] == dhm_to_check, "Photo"].values[0]
            ext = df.loc[df["Variation"] == dhm_to_check, "Extension"].values[0]

            if pd.isna(ext):
                ext = ".jpg"  # fallback

            url = f"{IMG_BASE}/{photo_name}{ext}"

            try:
                resp = requests.head(url, timeout=5)
                if resp.status_code == 200:
                    st.success(f"✅ Image exists at {url}")
                    st.image(url, caption=f"DHM {dhm_to_check}", use_container_width=True)
                else:
                    st.error(f"❌ No picture found at {url}")
            except Exception as e:
                st.error(f"Error checking image: {e}")
    else:
        st.info("No DHMs to check in the current filter.")


    # --- Drag and drop image upload ---
    st.markdown("---")
    st.subheader("Upload DHM Image")

    uploaded_file = st.file_uploader(
        "Drag and drop an image here",
        type=["jpg", "png", "jpeg", "HEIC"],
        key="image_uploader"
    )

    # Only show DHMs without an Extension value
    dhm_no_picture = df[df["Extension"].isna()]["Variation"].unique()


    dhm_for_image = st.selectbox(
            "Select DHM to associate with this image",
            options=dhm_no_picture,
            key="dhm_selectbox"
        )

    # Upload button
    if uploaded_file is not None and dhm_for_image:
        if st.button("Upload image"):
            # Determine original filename from CSV
            photo_name = df.loc[df["Variation"] == dhm_for_image, "Photo"].values[0]
            # Get the file extension from uploaded file
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            # Build save path
            save_path = os.path.join("DHMparis", f"{photo_name}{file_ext}")
            # Save the uploaded image
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Update extension in CSV if not HEIC
            if file_ext != ".heic":
                df.loc[df["Variation"] == dhm_for_image, "Extension"] = file_ext
                df.to_csv("DHMLISTING.csv", sep=";", index=False, encoding="latin1")

            st.success(f"📷 Image saved for DHM {dhm_for_image} at {save_path}")
