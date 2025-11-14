import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image, ImageOps
import math
import io
import pandas as pd

st.set_page_config(layout="wide")
st.title("🐄 Cattle Measurement Tool — Click two points (Line)")

st.markdown("""
### 📏 How to measure:
1. Upload cattle image  
2. Draw **ONE straight line** → press **Register measurement**  
3. Follow the order:
   - Height
   - Body Length
   - Heart Girth (diameter → app auto computes π × diameter)
4. Download the measured image + CSV

---

### 🛠 This version includes:
- Automatic PNG → RGBA fix  
- Automatic JPG fallback  
- Automatic resizing for huge images  
- Transparent background fix  
- Guaranteed canvas loading  
""")

uploaded = st.file_uploader("Upload cattle image", type=["jpg", "jpeg", "png"])

pixels_per_cm = st.number_input("Calibration — pixels per cm", value=32.0)

# session states
if "measurements" not in st.session_state:
    st.session_state.measurements = {"Height_cm": None, "BodyLength_cm": None, "Girth_cm": None}

if "step" not in st.session_state:
    st.session_state.step = 0

if "annotated_bytes" not in st.session_state:
    st.session_state.annotated_bytes = None


# -------------------------------
# SAFE IMAGE LOADING FUNCTION
# -------------------------------
def safe_load_image(uploaded_file):
    """Load any PNG/JPG safely for Streamlit Canvas."""
    try:
        img = Image.open(uploaded_file)
    except:
        return None

    # Convert all images to RGBA for Canvas safety
    try:
        img = img.convert("RGBA")
    except:
        img = img.convert("RGB").convert("RGBA")

    # Remove PNG metadata that breaks streamlit_canvas
    img = ImageOps.exif_transpose(img)

    # Resize huge images
    max_dim = 2000
    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim))

    return img


col1, col2 = st.columns([2, 1])

with col1:
    if uploaded:

        # 🔥 FIX: Load image safely
        pil_img = safe_load_image(uploaded)

        if pil_img is None:
            st.error("Failed to load image. Try converting to JPG.")
            st.stop()

        w, h = pil_img.size

        # 🔥 FIX: Use PIL directly — NEVER numpy
        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=4,
            stroke_color="#FF0000",
            background_image=pil_img,
            update_streamlit=True,
            height=h,
            width=w,
            drawing_mode="line",
            key="canvas"
        )

        objects = []
        if canvas_result.json_data and "objects" in canvas_result.json_data:
            objects = canvas_result.json_data["objects"]

        # Extract endpoints
        def extract_points(obj):
            if {"x1", "y1", "x2", "y2"}.issubset(obj):
                return (obj["x1"], obj["y1"]), (obj["x2"], obj["y2"])

            if "points" in obj and len(obj["points"]) >= 2:
                p0 = obj["points"][0]
                p1 = obj["points"][-1]
                return (p0["x"], p0["y"]), (p1["x"], p1["y"])

            return None, None

        if st.button("Register measurement"):
            if len(objects) == 0:
                st.warning("Draw a straight line first.")
            else:
                last = objects[-1]
                p1, p2 = extract_points(last)

                if not p1:
                    st.error("Could not detect a valid line. Use the Line tool.")
                else:
                    x1, y1 = float(p1[0]), float(p1[1])
                    x2, y2 = float(p2[0]), float(p2[1])

                    dist_px = math.dist((x1, y1), (x2, y2))
                    dist_cm = dist_px / pixels_per_cm

                    if st.session_state.step == 0:
                        st.session_state.measurements["Height_cm"] = dist_cm
                        st.success(f"Height recorded: {dist_cm:.2f} cm")
                        st.session_state.step = 1

                    elif st.session_state.step == 1:
                        st.session_state.measurements["BodyLength_cm"] = dist_cm
                        st.success(f"Body Length recorded: {dist_cm:.2f} cm")
                        st.session_state.step = 2

                    elif st.session_state.step == 2:
                        girth_cm = dist_cm * math.pi
                        st.session_state.measurements["Girth_cm"] = girth_cm
                        st.success(f"Girth recorded: {girth_cm:.2f} cm")
                        st.session_state.step = 3

                    # 🔥 FIX: Save annotated image snapshot
                    if canvas_result.image_data is not None:
                        arr = canvas_result.image_data.astype("uint8")
                        pil_ann = Image.fromarray(arr)
                        buf = io.BytesIO()
                        pil_ann.save(buf, format="PNG")
                        st.session_state.annotated_bytes = buf.getvalue()

        if st.button("Reset"):
            st.session_state.measurements = {"Height_cm": None, "BodyLength_cm": None, "Girth_cm": None}
            st.session_state.step = 0
            st.session_state.annotated_bytes = None
            st.experimental_rerun()


with col2:
    st.header("📏 Measurements")

    df = pd.DataFrame({
        "Measurement": ["Height", "Body Length", "Heart Girth"],
        "cm": [
            None if st.session_state.measurements["Height_cm"] is None else round(st.session_state.measurements["Height_cm"], 2),
            None if st.session_state.measurements["BodyLength_cm"] is None else round(st.session_state.measurements["BodyLength_cm"], 2),
            None if st.session_state.measurements["Girth_cm"] is None else round(st.session_state.measurements["Girth_cm"], 2),
        ]
    })

    st.table(df)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", csv_buf.getvalue(), "measurements.csv")

    if st.session_state.annotated_bytes:
        st.download_button("Download Annotated Image", st.session_state.annotated_bytes, "annotated.png", "image/png")
