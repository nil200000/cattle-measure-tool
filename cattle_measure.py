# cattle_measure_full.py
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image
import math
import io
import pandas as pd

st.set_page_config(layout="wide")
st.title("🐄 Cattle Measurement Tool — Click two points (Line)")

st.markdown(
    """
Draw a straight line (use the Line tool) for each measurement and press **Register measurement**:
1. Height (hoof → withers)
2. Body Length (shoulder → rump)
3. Heart Girth (diameter across chest) — circumference estimated as π * diameter

Notes: use the left toolbar's **Line** tool. Use Clear to remove drawing and draw again.
"""
)

uploaded = st.file_uploader("Upload cattle image", type=["jpg", "jpeg", "png"])
pixels_per_cm = st.number_input("Calibration — pixels per cm", value=32.0, format="%.4f")

# session state for measurements and annotated image bytes
if "measurements" not in st.session_state:
    st.session_state.measurements = {"Height_cm": None, "BodyLength_cm": None, "Girth_cm": None}
if "step" not in st.session_state:
    st.session_state.step = 0  # 0 height,1 length,2 girth,3 done
if "annotated_bytes" not in st.session_state:
    st.session_state.annotated_bytes = None

col1, col2 = st.columns([2,1])

with col1:
    if uploaded is not None:
        img = Image.open(uploaded).convert("RGB")
        img_arr = np.array(img)
        h, w = img_arr.shape[:2]

        # create canvas with image as background
        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=3,
            stroke_color="#ff0000",
            background_image=Image.fromarray(img_arr),
            update_streamlit=True,
            height=h,
            width=w,
            drawing_mode="line",
            key="canvas",
        )

        st.markdown("**Canvas controls:** Draw a straight line (press and drag). When ready, press **Register measurement**.")

        objects = []
        if canvas_result.json_data and "objects" in canvas_result.json_data:
            objects = canvas_result.json_data["objects"]

        def extract_line_endpoints(obj):
            if all(k in obj for k in ("x1", "y1", "x2", "y2")):
                return (obj["x1"], obj["y1"]), (obj["x2"], obj["y2"])
            if "points" in obj and isinstance(obj["points"], list) and len(obj["points"]) >= 2:
                p0 = obj["points"][0]
                p1 = obj["points"][-1]
                return (p0.get("x", p0.get("X")), p0.get("y", p0.get("Y"))), (p1.get("x", p1.get("X")), p1.get("y", p1.get("Y")))
            if all(k in obj for k in ("left", "top", "width", "height")):
                x1 = obj["left"]
                y1 = obj["top"]
                x2 = obj["left"] + obj["width"]
                y2 = obj["top"] + obj["height"]
                return (x1, y1), (x2, y2)
            return None, None

        st.write(f"Detected objects on canvas: {len(objects)} (draw exactly one straight line per measurement)")

        # When Register measurement pressed
        if st.button("Register measurement"):
            if len(objects) == 0:
                st.warning("No line detected. Please draw a straight line using the Line tool and try again.")
            else:
                last = objects[-1]
                p1, p2 = extract_line_endpoints(last)
                if p1 is None or p2 is None:
                    st.error("Couldn't extract endpoints from drawn object. Try drawing a straight line (not freehand).")
                else:
                    try:
                        x1, y1 = float(p1[0]), float(p1[1])
                        x2, y2 = float(p2[0]), float(p2[1])
                    except:
                        st.error("Invalid coordinates extracted from the drawn object.")
                        x1 = y1 = x2 = y2 = None

                    if x1 is not None:
                        dist_px = math.hypot(x2 - x1, y2 - y1)
                        dist_cm = dist_px / float(pixels_per_cm) if float(pixels_per_cm) > 0 else None

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
                            st.success(f"Heart Girth estimated: {girth_cm:.2f} cm (π * diameter)")
                            st.session_state.step = 3

                        # Save annotated image bytes from canvas (image_data)
                        if canvas_result.image_data is not None:
                            # image_data is RGBA float in [0..255]; convert to uint8 and save
                            img_annot = canvas_result.image_data
                            if img_annot.dtype != np.uint8:
                                img_annot = img_annot.astype(np.uint8)
                            # Convert to PIL and save to bytes
                            pil = Image.fromarray(img_annot)
                            buf = io.BytesIO()
                            pil.save(buf, format="PNG")
                            st.session_state.annotated_bytes = buf.getvalue()
                        else:
                            st.warning("Couldn't capture annotated image from canvas. You can screenshot the canvas as fallback.")

                        # Clear canvas for next measurement
                        st.session_state["canvas"] = None
                    else:
                        st.error("Couldn't compute measurement. Try drawing again.")

        if st.button("Reset all measurements"):
            st.session_state.measurements = {"Height_cm": None, "BodyLength_cm": None, "Girth_cm": None}
            st.session_state.step = 0
            st.session_state["canvas"] = None
            st.session_state.annotated_bytes = None
            st.experimental_rerun()

        # Show annotated preview if available (fallback to original)
        if st.session_state.annotated_bytes is not None:
            st.markdown("**Annotated preview (latest):**")
            st.image(st.session_state.annotated_bytes)
    else:
        st.info("Upload an image to start.")

with col2:
    st.header("Measurements")
    df = pd.DataFrame({
        "Measurement": ["Height (cm)", "Body Length (cm)", "Heart Girth (cm)"],
        "Value": [
            "-" if st.session_state.measurements["Height_cm"] is None else f"{st.session_state.measurements['Height_cm']:.2f}",
            "-" if st.session_state.measurements["BodyLength_cm"] is None else f"{st.session_state.measurements['BodyLength_cm']:.2f}",
            "-" if st.session_state.measurements["Girth_cm"] is None else f"{st.session_state.measurements['Girth_cm']:.2f}",
        ]
    })
    st.table(df)

    # Download CSV
    csv_buf = io.StringIO()
    saved = {k: (v if v is not None else "") for k, v in st.session_state.measurements.items()}
    pd.DataFrame([saved]).to_csv(csv_buf, index=False)
    st.download_button("Download measurements as CSV", csv_buf.getvalue(), file_name="measurements.csv")

    # Download annotated image if exists
    if st.session_state.get("annotated_bytes") is not None:
        st.download_button("Download annotated image (PNG)", st.session_state.annotated_bytes, file_name="annotated_measurement.png", mime="image/png")
    else:
        st.info("Annotated image will appear here after you register a measurement.")
