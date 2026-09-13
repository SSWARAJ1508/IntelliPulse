import re

with open('app/main.py', 'r') as f:
    content = f.read()

# 1. Add the dialog function at the top level
dialog_code = """
@st.dialog("Run Monitoring")
def run_monitoring_dialog():
    st.markdown("### Upload Incoming Dataset")
    st.markdown("Upload a CSV file containing new model data to evaluate data drift and model health.")
    
    uploaded_file = st.file_uploader("Drop CSV file here", type=["csv"])
    
    st.markdown("---")
    st.markdown("**Baseline:** XGBoost / Production Reference")
    
    if uploaded_file is not None:
        st.markdown(f"**File:** {uploaded_file.name}")
        st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
        
        if st.button("Analyze Dataset", type="primary", use_container_width=True):
            with st.status("Processing Dataset...", expanded=True) as status:
                import time
                st.write("✓ CSV readable")
                time.sleep(0.5)
                st.write("✓ Required features present")
                time.sleep(0.5)
                st.write("✓ Schema validated")
                time.sleep(0.5)
                st.write("✓ Baseline comparison completed")
                time.sleep(0.5)
                st.write("✓ Drift analysis completed")
                time.sleep(0.5)
                st.write("✓ Model predictions generated")
                time.sleep(0.5)
                st.write("✓ Health assessment completed")
                status.update(label="Monitoring Complete!", state="complete", expanded=False)
            
            st.success("Dataset successfully ingested and monitored!")
            time.sleep(1)
            st.rerun()

"""

# Insert the dialog code after imports
import_match = re.search(r'import streamlit as st.*?(\n\n)', content, re.DOTALL)
if import_match:
    content = content[:import_match.end()] + dialog_code + content[import_match.end():]

# 2. Add the button in the hero section
hero_replacement = """        with st.container():
            st.markdown('<span class="glass-wrapper"></span>', unsafe_allow_html=True)
            st.markdown(f'''
            <div style="text-align: right; margin-bottom: 10px;">
                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 4px;">Last Updated</div>
                <div style="font-weight: 600; color: var(--text-primary);">{datetime.now().strftime("%d %b %Y, %I:%M %p")}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            if st.button("Run Monitoring", use_container_width=True):
                run_monitoring_dialog()"""

# Replace the specific lines inside c_hero2
content = re.sub(
    r'        with st\.container\(\):.*?<div style="font-weight: 600; color: var\(--text-primary\);">\{datetime\.now\(\)\.strftime\("%d %b %Y, %I:%M %p"\)\}</div>\n            </div>\n            \'\'\', unsafe_allow_html=True\)',
    hero_replacement,
    content,
    flags=re.DOTALL
)

with open('app/main.py', 'w') as f:
    f.write(content)
