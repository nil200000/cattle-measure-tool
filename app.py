import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import math
import io
import pandas as pd

st.set_page_config(layout="wide")
st.title("🐄 Cattle Measurement Tool — Click two points")

uploaded = st.file_uploader("Upload cattle image", type=["jpg","jpeg","png"])
ppcm = st.number_input("Pixels per cm", value=32.0)

if "step" not in st.session_state:
    st.session_state.step = 0
if "measurements" not in st.session_state:
    st.session_state.measurements = {"Height":None,"BodyLength":None,"Girth":None}
if "annotated" not in st.session_state:
    st.session_state.annotated = None

def safe_pil(img):
    pil = Image.open(img)
    pil = pil.convert("RGBA")   # prevents PNG crash
    # resize huge if needed
    if pil.width > 2000 or pil.height > 2000:
        pil.thumbnail((2000,2000))
    return pil

if uploaded:
    pil = safe_pil(uploaded)
    w, h = pil.size

    st.write("Draw a straight line for the measurement step below:")

    step_msg = ["Step 1: Height","Step 2: Body Length","Step 3: Girth (diameter)"]
    if st.session_state.step < 3:
        st.info(step_msg[st.session_state.step])
    else:
        st.success("All measurements completed.")

    canvas = st_canvas(
        stroke_width=4,
        stroke_color="red",
        background_image=pil,
        height=h,
        width=w,
        drawing_mode="line",
        key="canvas"
    )

    if st.button("Register measurement"):
        if not canvas.json_data or "objects" not in canvas.json_data or len(canvas.json_data["objects"]) == 0:
            st.warning("Draw a straight line first.")
        else:
            obj = canvas.json_data["objects"][-1]

            # extract endpoints
            x1, y1 = obj["x1"], obj["y1"]
            x2, y2 = obj["x2"], obj["y2"]

            dist_px = math.dist((x1,y1),(x2,y2))
            dist_cm = dist_px / ppcm

            if st.session_state.step == 0:
                st.session_state.measurements["Height"] = dist_cm
            elif st.session_state.step == 1:
                st.session_state.measurements["BodyLength"] = dist_cm
            elif st.session_state.step == 2:
                st.session_state.measurements["Girth"] = dist_cm * math.pi

            st.session_state.step += 1

            # save annotated image
            if canvas.image_data is not None:
                arr = canvas.image_data.astype(np.uint8)
                out = Image.fromarray(arr)
                buf = io.BytesIO()
                out.save(buf, format="PNG")
                st.session_state.annotated = buf.getvalue()

    # Download buttons
    st.write("### Measurements")
    df = pd.DataFrame({
        "Measurement":["Height","Body Length","Girth"],
        "cm":[
            st.session_state.measurements["Height"],
            st.session_state.measurements["BodyLength"],
            st.session_state.measurements["Girth"]
        ]
    })
    st.table(df)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", csv_buf.getvalue(), "measurements.csv")

    if st.session_state.annotated:
        st.download_button("Download Annotated Image", st.session_state.annotated,
                           "annotated.png", "image/png")
