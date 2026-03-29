import streamlit as st
import csv
import io
from pathlib import Path

st.set_page_config(page_title="CSV to ARFF Converter", page_icon="📊", layout="centered")

st.title("📊 CSV to ARFF Converter")
st.markdown("**Weka ke liye Smart CSV → ARFF Converter**")

def validate_csv_for_weka(csv_bytes: bytes):
    """Pehle check karta hai ki ARFF Weka mein chalegi ya nahi"""
    try:
        text = csv_bytes.decode('utf-8')
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        
        if len(rows) < 2:
            return False, "CSV mein sirf header hai ya koi data nahi hai. Kam se kam 1 data row hona chahiye."
        
        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:]
        
        # 1. Empty header check (sabse common error - Jobs.csv jaisa)
        empty_headers = [i for i, h in enumerate(headers) if not h]
        if empty_headers:
            cols = ", ".join([f"Column {i+1}" for i in empty_headers])
            return False, f"❌ **Empty column name(s) detected**\n\nPehle column ka naam khali hai ({cols}).\n\n**Fix:** CSV file kholo aur khali column ko naam de do (jaise 'id', 'sr_no' etc.)"
        
        # 2. Inconsistent column count
        num_cols = len(headers)
        inconsistent_rows = []
        for idx, row in enumerate(data_rows, start=2):
            if len(row) != num_cols:
                inconsistent_rows.append(f"Row {idx} (has {len(row)} columns instead of {num_cols})")
        
        if inconsistent_rows:
            return False, f"❌ **Column count mismatch**\n\nSabhi rows mein same number of columns nahi hain.\n\n{chr(10).join(inconsistent_rows[:5])}\n\n**Fix:** CSV mein har row mein exactly {num_cols} columns rakho (trailing commas hatao)."
        
        # 3. Header row completely empty
        if all(not h for h in headers):
            return False, "❌ Header row completely empty hai. Pehli line mein column names hone chahiye."
        
        return True, "Validation passed ✅"
        
    except Exception as e:
        return False, f"CSV file padhne mein error: {str(e)}"

def csv_to_arff(csv_bytes: bytes, filename: str):
    """Actual conversion (sirf tabhi call hoga jab validation pass ho)"""
    text = csv_bytes.decode('utf-8')
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    
    headers = [h.strip() for h in rows[0]]
    data_rows = rows[1:]
    
    # Clean headers (already validated so no empty)
    clean_headers = [h.replace(" ", "_").replace("-", "_").replace(",", "_") for h in headers]
    
    num_cols = len(clean_headers)
    cleaned_data = []
    for row in data_rows:
        row = [str(x).strip() for x in row]
        if len(row) < num_cols:
            row += [""] * (num_cols - len(row))
        cleaned_data.append(row[:num_cols])
    
    # Type detection
    def detect_type(values):
        values = [v for v in values if v.strip()]
        if not values:
            return "STRING"
        try:
            [float(v) for v in values]
            return "NUMERIC"
        except:
            unique = list(set(values))
            if len(unique) <= 20:
                escaped = [f"'{val}'" if any(c in val for c in " ,'" ) else val for val in unique]
                return "{" + ",".join(escaped) + "}"
            return "STRING"
    
    columns = list(zip(*cleaned_data)) if cleaned_data else [[]] * num_cols
    attr_types = [detect_type(col) for col in columns]
    
    # Build ARFF
    relation = Path(filename).stem.replace(" ", "_").replace("-", "_")
    arff_lines = [f"@RELATION {relation}"]
    
    for header, atype in zip(clean_headers, attr_types):
        arff_lines.append(f"@ATTRIBUTE {header} {atype}")
    
    arff_lines.append("\n@DATA")
    
    for row in cleaned_data:
        formatted = []
        for val in row:
            if not val:
                formatted.append("?")
            elif any(c in val for c in ", '") or "₹" in val:
                formatted.append(f"'{val}'")
            else:
                formatted.append(val)
        arff_lines.append(",".join(formatted))
    
    return "\n".join(arff_lines)

# ====================== STREAMLIT UI ======================
uploaded_file = st.file_uploader("Upload CSV File", type=["csv"], help="Weka compatible ARFF banane ke liye")

if uploaded_file:
    st.success(f"✅ File uploaded: **{uploaded_file.name}**")
    
    # VALIDATION BUTTON
    if st.button("🔍 Check if this CSV will work in Weka", type="secondary", use_container_width=True):
        with st.spinner("Validating CSV for Weka..."):
            is_valid, message = validate_csv_for_weka(uploaded_file.getvalue())
            
            if is_valid:
                st.success("🎉 **Validation Passed!** Ye file Weka mein perfectly chalegi.")
            else:
                st.error("❌ **Validation Failed**")
                st.markdown(message)
                st.warning("**Convert button abhi disable hai.** Pehle CSV ko upar diye fix ke hisaab se sahi karo, phir dobara upload karke try karo.")
    
    # CONVERT BUTTON (sirf tab dikhega jab validation pass ho)
    if st.button("🔄 Convert to ARFF", type="primary", use_container_width=True):
        with st.spinner("Validating + Converting..."):
            is_valid, message = validate_csv_for_weka(uploaded_file.getvalue())
            
            if not is_valid:
                st.error("❌ Ye file Weka mein nahi chalegi")
                st.markdown(message)
            else:
                try:
                    arff_content = csv_to_arff(uploaded_file.getvalue(), uploaded_file.name)
                    arff_name = Path(uploaded_file.name).stem + ".arff"
                    
                    st.success("🎉 Conversion Successful! Ab ye ARFF Weka mein bilkul sahi chalegi.")
                    
                    st.download_button(
                        label="💾 Download ARFF File",
                        data=arff_content,
                        file_name=arff_name,
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                    st.subheader("ARFF Preview (first 12 lines)")
                    st.code("\n".join(arff_content.splitlines()[:12]), language=None)
                    
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")

st.caption("Smart Validator + Converter | Empty headers & column mismatch auto-detect karta hai")
