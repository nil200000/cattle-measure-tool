import streamlit as st
from streamlit_image_annotation import annotate
from PIL import Image
import numpy as np
import pandas as pd
import math
import io

st.set_page_config(layout="wide")
st.title("🐄 Cattle Measurement Tool — Click two points (Line)")

uploaded = st.file_uploader("Upload cattle image", type=["jpg","jpeg","png"])
pixels_per_cm = st.number_input("Pixels per cm", value=32.0)

if "step" not in st.session_state:
    st.session_state.step = 0

if "measurements" not in st.session_state:
    st.session_state.measurements = {"Height":None, "Body Length":None, "Girth":None}

if uploaded:
    pil = Image.open(uploaded).convert("RGB")
    w,h = pil.size

    st.write("Draw a straight line for:")
    if st.session_state.step == 0: st.info("STEP 1: Height")
    if st.session_state.step == 1: st.info("STEP 2: Body Length")
    if st.session_state.step == 2: st.info("STEP 3: Heart Girth (diameter)")
    if st.session_state.step >= 3: st.success("All measurements completed.")

    result = annotate(
        pil,
        shapes=["line"],
        stroke_width=4,
        height=h,
        width=w,
        stroke_color="red"
    )

    if st.button("Register measurement"):
        if not result["lines"]:
            st.warning("Draw a line first.")
        else:
            x1,y1,x2,y2 = result["lines"][-1]

            dist_px = math.dist((x1,y1),(x2,y2))
            dist_cm = dist_px / pixels_per_cm

            if st.session_state.step == 0:
                st.session_state.measurements["Height"] = dist_cm
                st.session_state.step = 1
                st.success(f"Height recorded: {dist_cm:.2f} cm")

            elif st.session_state.step == 1:
                st.session_state.measurements["Body Length"] = dist_cm
                st.session_state.step = 2
                st.success(f"Body Length recorded: {dist_cm:.2f} cm")

            elif st.session_state.step == 2:
                st.session_state.measurements["Girth"] = dist_cm * math.pi
                st.session_state.step = 3
                st.success(f"Girth recorded: {dist_cm*math.pi:.2f} cm")

    st.write("")
    st.header("Measurements")

    df = pd.DataFrame({
        "Measurement":["Height","Body Length","Girth"],
        "cm":[
            None if st.session_state.measurements["Height"] is None else round(st.session_state.measurements["Height"],2),
            None if st.session_state.measurements["Body Length"] is None else round(st.session_state.measurements["Body Length"],2),
            None if st.session_state.measurements["Girth"] is None else round(st.session_state.measurements["Girth"],2)
        ]
    })

    st.table(df)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", csv_buf.getvalue(), "measurements.csv")
