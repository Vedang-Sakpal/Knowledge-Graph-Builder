import streamlit as st
import pandas as pd
import json
import os
import subprocess
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import tempfile
import shutil

# Try to import config, create basic one if not found
try:
    import config
except ImportError:
    st.error("❌ config.py not found! Please create your configuration file.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="HAZOP Analysis Platform",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .upload-box {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        background-color: #f8f9ff;
    }
    .file-item {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
        color: #721c24;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
        color: #0c5460;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar styling */
    .sidebar-nav {
        margin: 0.5rem 0;
    }
    
    /* Custom button styling for active state */
    .stButton > button {
        width: 100%;
        text-align: left;
        border-radius: 8px;
        border: 1px solid #ddd;
        padding: 0.75rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        border-color: #1f77b4;
        box-shadow: 0 2px 4px rgba(31, 119, 180, 0.2);
    }
    
    /* Active page highlight */
    div[data-testid="stSidebar"] .element-container:has(.stButton button[kind="primary"]) {
        background: linear-gradient(90deg, rgba(31, 119, 180, 0.1), transparent);
        border-radius: 8px;
        padding: 0.25rem;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Add this function to your streamlit_app.py file
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_equipment_from_db():
    """Queries the Neo4j database to get a list of all equipment."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("MATCH (e:Equipment) RETURN e.name AS name, e.type AS type ORDER BY name")
            equipment_list = [{"name": record["name"], "type": record["type"]} for record in result]
        driver.close()
        return equipment_list
    except Exception as e:
        st.error(f"Failed to connect to Neo4j: {e}")
        return []

def format_section_content(text):
    """Ensure section content follows consistent formatting"""
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Preserve headers and bullet points
            if line.startswith(('#', '-', '*', '•')) or line.isupper():
                formatted_lines.append(line)
            else:
                # Ensure proper sentence casing for regular text
                if line and not line[0].isupper():
                    line = line[0].upper() + line[1:]
                formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        'current_stage': 0,
        'pipeline_running': False,
        'uploaded_files': {'pid': [], 'msds': []},
        'execution_log': [],
        'config_validated': False,
        # Enhanced description verification state
        'desc_sections': [],        # list of description sections for review
        'desc_approved': False,     # set True after human approval
        'pipeline_paused_at': None, # stage index where pipeline paused for review
        'pipeline_resume': False,   # flag to auto-resume pipeline after approval
        # File selections for current session
        'current_pid_file': None,
        'current_process_description': None,
        'current_equipment': None,
        # Human checkpoint control
        'checkpoint_active': False   # New: track if checkpoint is active
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def create_upload_directories():
    """Create necessary upload directories"""
    directories = [
        "P&ID",
        "MSDS", 
        "Context for RAG",
        "Process Description",
        "Results",
        "temp_uploads/pid",
        "temp_uploads/msds"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def validate_cypher_file(file_content):
    """Validate Cypher file content"""
    try:
        # Basic validation - check for common Cypher keywords
        cypher_keywords = ['CREATE', 'MERGE', 'MATCH', 'SET', 'RETURN']
        content_upper = file_content.upper()
        
        has_cypher = any(keyword in content_upper for keyword in cypher_keywords)
        
        if has_cypher:
            return True, "Valid Cypher file"
        else:
            return False, "File doesn't appear to contain Cypher statements"
    except Exception as e:
        return False, f"Error validating file: {str(e)}"

def save_uploaded_file(uploaded_file, target_directory):
    """Save uploaded file to target directory"""
    try:
        file_path = Path(target_directory) / uploaded_file.name
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def get_file_info(file_path):
    """Get file information"""
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'exists': True
        }
    except:
        return {'exists': False}

def run_pipeline_stage(script_name, stage_name, args_list=None):
    """Run a single pipeline stage with proper argument handling"""
    try:
        start_time = time.time()
        
        # Build the command with arguments
        command = ['python', script_name]
        if args_list:
            command.extend(args_list)  # Add arguments to the command
            
        # Log stage start
        log_entry = {
            "timestamp": datetime.now(),
            "stage": stage_name,
            "status": "started",
            "script": script_name,
            "command": " ".join(command)  # Log the full command
        }
        st.session_state.execution_log.append(log_entry)
        
        # Execute the script with arguments
        result = subprocess.run(
            command,  # Use the full command with arguments
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        execution_time = time.time() - start_time
        success = result.returncode == 0
        
        # Log completion
        log_entry = {
            "timestamp": datetime.now(),
            "stage": stage_name,
            "status": "completed" if success else "failed",
            "execution_time": execution_time,
            "script": script_name,
            "command": " ".join(command),
            "return_code": result.returncode,
            "output": result.stdout if success else result.stderr
        }
        st.session_state.execution_log.append(log_entry)
        
        return success, result.stdout if success else result.stderr, execution_time
        
    except subprocess.TimeoutExpired:
        return False, "Script execution timed out (5 minutes)", 0
    except Exception as e:
        return False, str(e), 0

def show_human_checkpoint():
    """Enhanced human checkpoint for description verification with full-page editing"""
    st.subheader("🔎 Mandatory Human Checkpoint: Verify Generated Description")
    st.warning("⚠️ **Mandatory Verification Required** - Please review and approve the generated description before proceeding.")
    
    desc_output_file = os.path.join("Process Description", "generated_description.txt")
    if not os.path.exists(desc_output_file):
        st.error("No description file generated. Please run the previous stages first.")
        return False

    # Read the generated description
    with open(desc_output_file, "r", encoding='utf-8') as f:
        desc_text = f.read()

    st.markdown("### 📋 Generated Process Description")
    st.info("💡 **Instructions:** Review the entire description below. You can edit the content directly as needed.")
    
    # Display the full description in a large editable text area
    edited_description = st.text_area(
        "Edit the process description:",
        value=desc_text,
        height=400,  # Increased height for better visibility
        key="full_description_editor",
        help="Make any necessary changes to the generated description"
    )
    
    # Show character count and other stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Characters", len(edited_description))
    with col2:
        st.metric("Lines", len(edited_description.split('\n')))
    with col3:
        st.metric("Words", len(edited_description.split()))
    
    # Preview of the edited description
    with st.expander("👁️ Preview Edited Description", expanded=False):
        st.text_area(
            "Preview (read-only):", 
            edited_description, 
            height=200, 
            disabled=True,
            key="description_preview"
        )
    
    st.markdown("---")
    st.markdown("### ✅ Approval Control")
    
    # Approval buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("✅ Approve and Continue", type="primary", use_container_width=True):
            # Save the approved/edited description
            approved_file = os.path.join("Process Description", "approved_description.txt")
            
            with open(approved_file, "w", encoding='utf-8') as f:
                f.write(edited_description)
            
            st.session_state.desc_approved = True
            st.session_state.pipeline_resume = True
            st.success("✅ Description approved! Pipeline will continue.")
            
            # Also update the session state with the edited content
            st.session_state.desc_sections = [edited_description]  # Store as single section
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset to Original", use_container_width=True):
            # Reset to original content
            st.session_state.desc_approved = False
            st.session_state.desc_sections = []  # Clear sections to force reload
            st.info("Description reset to original. Please review again.")
            st.rerun()
    
    with col3:
        if st.button("💾 Save Draft", use_container_width=True):
            # Save current edits as draft without approving
            draft_file = os.path.join("Process Description", "draft_description.txt")
            with open(draft_file, "w", encoding='utf-8') as f:
                f.write(edited_description)
            st.success("💾 Draft saved! You can continue editing.")
    
    # Show file status
    st.markdown("---")
    st.markdown("### 📊 File Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        original_exists = os.path.exists(desc_output_file)
        if original_exists:
            original_size = os.path.getsize(desc_output_file)
            st.success(f"📄 Original: {original_size} bytes")
        else:
            st.error("❌ Original: Missing")
    
    with col2:
        approved_exists = os.path.exists(os.path.join("Process Description", "approved_description.txt"))
        if approved_exists:
            st.success("✅ Approved: Exists")
        else:
            st.info("⏳ Approved: Not yet")
    
    with col3:
        draft_exists = os.path.exists(os.path.join("Process Description", "draft_description.txt"))
        if draft_exists:
            st.info("📝 Draft: Exists")
        else:
            st.info("📝 Draft: Not saved")
    
    return st.session_state.desc_approved

def get_file_selection_confirmation(file_type, available_files, current_selection, help_text=""):
    """Get file selection with confirmation for a specific stage"""
    st.markdown(f"### 📋 {file_type} Selection")
    
    if not available_files:
        st.error(f"No {file_type.lower()} files available. Please upload files first.")
        return None
    
    # File selection
    selected_file = st.selectbox(
        f"Select {file_type}:",
        available_files,
        index=available_files.index(current_selection) if current_selection in available_files else 0,
        key=f"{file_type.lower().replace(' ', '_')}_selector",
        help=help_text
    )
    
    # Confirmation
    if st.button(f"✅ Confirm {file_type} Selection", key=f"confirm_{file_type.lower().replace(' ', '_')}"):
        st.success(f"✅ {file_type} confirmed: {selected_file}")
        return selected_file
    
    return current_selection if current_selection else None

def get_equipment_selection_confirmation(available_equipment, current_selection):
    """Get equipment selection with confirmation for a specific stage"""
    st.markdown("### 🔧 Equipment Selection")
    
    if not available_equipment:
        st.error("No equipment found in database. Run previous stages first.")
        return None
    
    equipment_options = [f"{eq['name']} ({eq['type']})" for eq in available_equipment]
    
    # Equipment selection
    selected_option = st.selectbox(
        "Select equipment:",
        equipment_options,
        index=equipment_options.index(current_selection) if current_selection in equipment_options else 0,
        key="equipment_selector",
        help="Select equipment for HAZOP analysis"
    )
    
    # Find the selected equipment data
    selected_eq_data = next((eq for eq in available_equipment if f"{eq['name']} ({eq['type']})" == selected_option), None)
    
    # Confirmation
    if st.button("✅ Confirm Equipment Selection", key="confirm_equipment"):
        if selected_eq_data:
            st.success(f"✅ Equipment confirmed: {selected_eq_data['name']} ({selected_eq_data['type']})")
            return selected_eq_data
    
    return current_selection if current_selection else None

def main():
    """Main application"""
    initialize_session_state()
    create_upload_directories()
    
    # Header
    st.markdown('<div class="main-header">HAZOP Analysis Platform</div>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🎛️ Control Panel")
        
        # Initialize page selection in session state
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "🏠 Dashboard"
        
        st.markdown("### 📍 Navigation")
        
        # Navigation buttons with better visual feedback
        pages = [
            ("🏠 Dashboard", "🏠", "Main overview and system status"),
            ("📤 File Upload", "📤", "Upload P&ID and MSDS files"), 
            ("🚀 Pipeline Execution", "🚀", "Run HAZOP analysis pipeline"),
            ("📊 Results", "📊", "View and download reports"),
            ("⚙️ Configuration", "⚙️", "System settings and validation")
        ]
        
        for page_name, icon, description in pages:
            # Check if this is the current page
            is_current = st.session_state.current_page == page_name
            
            # Create a container for better styling
            button_container = st.container()
            
            with button_container:
                # Show active page indicator
                if is_current:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(90deg, rgba(31, 119, 180, 0.15), transparent);
                        border-left: 4px solid #1f77b4;
                        border-radius: 8px;
                        padding: 0.5rem;
                        margin: 0.25rem 0;
                    ">
                        <strong>{icon} {page_name.split(' ', 1)[1]} ← Current</strong><br>
                        <small style="color: #666;">{description}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Regular navigation button
                    if st.button(f"{icon} {page_name.split(' ', 1)[1]}", 
                                key=f"nav_{page_name}", 
                                help=description,
                                use_container_width=True):
                        st.session_state.current_page = page_name
                        st.rerun()
        
        # Get the selected page for routing
        page = st.session_state.current_page
        
        st.markdown("---")
        st.subheader("📊 Quick Stats")
        
        # Quick stats with better formatting
        pid_files = len([f for f in os.listdir("P&ID") if f.endswith('.cypher')]) if os.path.exists("P&ID") else 0
        msds_files = len([f for f in os.listdir("MSDS") if f.endswith(('.pdf', '.txt'))]) if os.path.exists("MSDS") else 0
        
        # Create metrics with color coding
        col1, col2 = st.columns(2)
        with col1:
            if pid_files > 0:
                st.success(f"📊 P&ID Files\n**{pid_files}** uploaded")
            else:
                st.warning(f"📊 P&ID Files\n**{pid_files}** uploaded")
        
        with col2:
            if msds_files > 0:
                st.success(f"🧪 MSDS Files\n**{msds_files}** uploaded")
            else:
                st.warning(f"🧪 MSDS Files\n**{msds_files}** uploaded")
        
        # Pipeline progress
        progress = st.session_state.current_stage
        progress_percentage = (progress / 8) * 100
        
        st.markdown(f"**🚀 Pipeline Progress:** {progress}/8")
        st.progress(progress / 8)
        
        if progress == 0:
            st.info("Ready to start pipeline")
        elif progress < 8:
            st.warning(f"{progress_percentage:.0f}% complete")
        else:
            st.success("Pipeline completed! ✅")
        
        # Quick actions
        st.markdown("---")
        st.subheader("⚡ Quick Actions")
        
        # Status indicators
        if st.button("🔄 Refresh Status", key="refresh_sidebar", use_container_width=True):
            st.rerun()
        
        if st.button("🗂️ View All Files", key="quick_files", use_container_width=True):
            st.session_state.current_page = "📤 File Upload"
            st.rerun()
        
        if st.button("▶️ Start Pipeline", key="quick_pipeline", use_container_width=True):
            st.session_state.current_page = "🚀 Pipeline Execution"
            st.rerun()
        
        # System status indicators
        st.markdown("---")
        st.subheader("🔧 System Status")
        
        # Check basic system health
        config_ok = hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY != 'your_gemini_api_key_here'
        ontology_ok = os.path.exists('HAZOP_Ontology_CLEAN.rdf')
        context_ok = os.path.exists('Context for RAG/Parameter and guideword.csv')
        
        if config_ok:
            st.success("✅ Configuration")
        else:
            st.error("❌ Configuration")
        
        if ontology_ok:
            st.success("✅ Ontology File")
        else:
            st.error("❌ Ontology File")
        
        if context_ok:
            st.success("✅ Context Data")
        else:
            st.error("❌ Context Data")
    
    # Route to selected page
    if "Dashboard" in page:
        show_dashboard()
    elif "File Upload" in page:
        show_file_upload()
    elif "Pipeline Execution" in page:
        show_pipeline_execution()
    elif "Results" in page:
        show_results()
    elif "Configuration" in page:
        show_configuration()

def show_dashboard():
    """Dashboard overview"""
    st.header("🏠 Dashboard Overview")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pid_count = len([f for f in os.listdir("P&ID") if f.endswith('.cypher')]) if os.path.exists("P&ID") else 0
        st.markdown(f"""
            <div class="metric-card">
                <h3>📊 P&ID Files</h3>
                <h1>{pid_count}</h1>
                <p>Uploaded</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        msds_count = len([f for f in os.listdir("MSDS") if f.endswith(('.pdf', '.txt'))]) if os.path.exists("MSDS") else 0
        st.markdown(f"""
            <div class="metric-card">
                <h3>🧪 MSDS Files</h3>
                <h1>{msds_count}</h1>
                <p>Uploaded</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        progress = st.session_state.current_stage
        st.markdown(f"""
            <div class="metric-card">
                <h3>🚀 Pipeline</h3>
                <h1>{progress}/8</h1>
                <p>Completed</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        results_count = len([f for f in os.listdir("Results") if f.endswith(('.xlsx', '.json'))]) if os.path.exists("Results") else 0
        st.markdown(f"""
            <div class="metric-card">
                <h3>📋 Reports</h3>
                <h1>{results_count}</h1>
                <p>Generated</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # System status
    st.subheader("🔧 System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Required Files Status")
        
        # Check required files
        required_files = [
            ("HAZOP_Ontology_CLEAN.rdf", "Ontology File"),
            ("Context for RAG/Equipment_and_Deviation.csv", "Equipment Data")
        ]
        
        for file_path, description in required_files:
            if os.path.exists(file_path):
                st.success(f"✅ {description}")
            else:
                st.error(f"❌ {description} - Missing")
    
    with col2:
        st.markdown("### 📊 Pipeline Stages")
        
        stages = [
            "P&ID Parsing", "Ontology Loading", "Semantic Enrichment",
            "Process Understanding", "Deviation Generation",
            "HAZOP Analysis", "Verification"
        ]
        
        for i, stage in enumerate(stages):
            if i < st.session_state.current_stage:
                st.success(f"✅ Stage {i+1}: {stage}")
            elif i == st.session_state.current_stage and st.session_state.pipeline_running:
                st.warning(f"⏳ Stage {i+1}: {stage} (Running)")
            else:
                st.info(f"⏸️ Stage {i+1}: {stage}")
    
    # Recent activity
    if st.session_state.execution_log:
        st.markdown("---")
        st.subheader("📋 Recent Activity")
        
        recent_logs = st.session_state.execution_log[-5:]
        for log in reversed(recent_logs):
            timestamp = log['timestamp'].strftime("%H:%M:%S")
            stage = log['stage']
            status = log['status']
            
            if status == "completed":
                st.success(f"🟢 {timestamp} - {stage}: Completed")
            elif status == "failed":
                st.error(f"🔴 {timestamp} - {stage}: Failed")
            else:
                st.info(f"🟡 {timestamp} - {stage}: {status.title()}")

def show_file_upload():
    """Enhanced file upload interface"""
    st.header("📤 File Upload Center")
    
    # Create tabs for different file types
    tab1, tab2, tab3 = st.tabs(["📊 P&ID Files", "🧪 MSDS Files", "📁 File Browser"])
    
    with tab1:
        st.subheader("📊 P&ID Cypher File Upload")
        st.markdown("""
        <div class="info-box">
        <strong>📋 Instructions:</strong><br>
        • Upload your P&ID Cypher files (.cypher extension)<br>
        • Files should contain CREATE/MERGE statements for your process<br>
        • Multiple files can be uploaded at once<br>
        • Files will be validated automatically
        </div>
        """, unsafe_allow_html=True)
        
        # P&ID file upload
        pid_uploaded_files = st.file_uploader(
            "Choose P&ID Cypher files",
            type=['cypher'],
            accept_multiple_files=True,
            key="pid_uploader"
        )
        
        if pid_uploaded_files:
            st.markdown("### 📋 Processing Uploaded Files...")
            
            for uploaded_file in pid_uploaded_files:
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**📄 {uploaded_file.name}**")
                
                with col2:
                    file_size = len(uploaded_file.getvalue()) / 1024
                    st.write(f"{file_size:.1f} KB")
                
                with col3:
                    # Validate and save file
                    file_content = uploaded_file.getvalue().decode('utf-8')
                    is_valid, message = validate_cypher_file(file_content)
                    
                    if is_valid:
                        success, file_path = save_uploaded_file(uploaded_file, "P&ID")
                        if success:
                            st.success("✅ Saved")
                            
                            # Update config.py PID_PATH if this is the first/main file
                            if not hasattr(config, 'PID_PATH') or not os.path.exists(getattr(config, 'PID_PATH', '')):
                                try:
                                    with open('config.py', 'r') as f:
                                        config_content = f.read()
                                    
                                    # Update PID_PATH
                                    if 'PID_PATH' in config_content:
                                        config_content = config_content.replace(
                                            f'PID_PATH = "{getattr(config, "PID_PATH", "")}"',
                                            f'PID_PATH = "{file_path}"'
                                        )
                                    else:
                                        config_content += f'\nPID_PATH = "{file_path}"\n'
                                    
                                    with open('config.py', 'w') as f:
                                        f.write(config_content)
                                    
                                    st.info(f"📝 Updated config.py with PID_PATH: {file_path}")
                                except Exception as e:
                                    st.warning(f"Could not update config.py: {e}")
                        else:
                            st.error("❌ Failed")
                    else:
                        st.error(f"❌ {message}")
        
        # Show existing P&ID files
        st.markdown("---")
        st.subheader("📂 Existing P&ID Files")
        
        if os.path.exists("P&ID"):
            pid_files = [f for f in os.listdir("P&ID") if f.endswith('.cypher')]
            
            if pid_files:
                for file in pid_files:
                    file_path = os.path.join("P&ID", file)
                    file_info = get_file_info(file_path)
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                    
                    with col1:
                        st.write(f"📄 **{file}**")
                    
                    with col2:
                        if file_info['exists']:
                            st.write(f"{file_info['size']/1024:.1f} KB")
                    
                    with col3:
                        if file_info['exists']:
                            st.write(file_info['modified'].strftime("%Y-%m-%d %H:%M"))
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"del_pid_{file}"):
                            os.remove(file_path)
                            st.success("File deleted!")
                            st.rerun()
            else:
                st.info("No P&ID files uploaded yet.")
        else:
            st.info("P&ID directory not found.")
    
    with tab2:
        st.subheader("🧪 MSDS File Upload")
        st.markdown("""
        <div class="info-box">
        <strong>📋 Instructions:</strong><br>
        • Upload MSDS files in PDF or TXT format<br>
        • Files should contain chemical safety data sheets<br>
        • System will extract chemical names automatically<br>
        • Files will be processed for semantic enrichment
        </div>
        """, unsafe_allow_html=True)
        
        # MSDS file upload
        msds_uploaded_files = st.file_uploader(
            "Choose MSDS files",
            type=['pdf', 'txt'],
            accept_multiple_files=True,
            key="msds_uploader"
        )
        
        if msds_uploaded_files:
            st.markdown("### 📋 Processing MSDS Files...")
            
            for uploaded_file in msds_uploaded_files:
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**📄 {uploaded_file.name}**")
                
                with col2:
                    file_size = len(uploaded_file.getvalue()) / 1024
                    st.write(f"{file_size:.1f} KB")
                
                with col3:
                    success, file_path = save_uploaded_file(uploaded_file, "MSDS")
                    if success:
                        st.success("✅ Saved")
                    else:
                        st.error("❌ Failed")
        
        # Show existing MSDS files
        st.markdown("---")
        st.subheader("📂 Existing MSDS Files")
        
        if os.path.exists("MSDS"):
            msds_files = [f for f in os.listdir("MSDS") if f.endswith(('.pdf', '.txt'))]
            
            if msds_files:
                for file in msds_files:
                    file_path = os.path.join("MSDS", file)
                    file_info = get_file_info(file_path)
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                    
                    with col1:
                        st.write(f"📄 **{file}**")
                    
                    with col2:
                        if file_info['exists']:
                            st.write(f"{file_info['size']/1024:.1f} KB")
                    
                    with col3:
                        if file_info['exists']:
                            st.write(file_info['modified'].strftime("%Y-%m-%d %H:%M"))
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"del_msds_{file}"):
                            os.remove(file_path)
                            st.success("File deleted!")
                            st.rerun()
            else:
                st.info("No MSDS files uploaded yet.")
        else:
            st.info("MSDS directory not found.")
    
    with tab3:
        st.subheader("📁 Complete File Browser")
        
        directories = {
            "📊 P&ID": "P&ID",
            "🧪 MSDS": "MSDS", 
            "📋 Context": "Context for RAG",
            "📖 Process": "Process Description",
            "📊 Results": "Results"
        }
        
        for display_name, directory in directories.items():
            with st.expander(f"{display_name} Directory"):
                if os.path.exists(directory):
                    files = os.listdir(directory)
                    if files:
                        total_size = 0
                        for file in files:
                            file_path = os.path.join(directory, file)
                            if os.path.isfile(file_path):
                                size = os.path.getsize(file_path)
                                total_size += size
                                modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                                
                                col1, col2, col3 = st.columns([3, 1, 2])
                                with col1:
                                    st.write(f"📄 {file}")
                                with col2:
                                    st.write(f"{size/1024:.1f} KB")
                                with col3:
                                    st.write(modified.strftime("%Y-%m-%d %H:%M"))
                        
                        st.info(f"📊 Total: {len(files)} files, {total_size/1024:.1f} KB")
                    else:
                        st.write("📂 Empty directory")
                else:
                    st.error(f"❌ Directory '{directory}' not found")
                    
def show_pipeline_execution():
    """Pipeline execution interface with file selection at each stage"""
    st.header("🚀 Pipeline Execution")
    
    # Pipeline stages
    stages = [
        ("01_parsing_P&ID.py", "📊 P&ID Parsing", "Load P&ID data into Neo4j"),
        ("02_ontology_loader.py", "🏗️ Ontology Loading", "Apply HAZOP schema constraints"), 
        ("03_semantic_enrichment.py", "🧠 Semantic Enrichment", "Enrich with chemical data"),
        ("04_equipment_node.py","📝 Description Generation", "Generate equipment descriptions"),
        ("05_Understanding_process_using_LLM.py", "📖 Process Understanding", "Generate process descriptions"),
        ("06_Generate_applicable_deviations.py", "⚠️ Deviation Generation", "Create equipment deviations"),
        ("07_HAZOP_analysis.py", "🔍 HAZOP Analysis", "Perform main analysis"),
        ("08_verify_accuracy.py", "✅ Verification", "Verify results")
    ]
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ Run Full Pipeline", 
                    type="primary", 
                    disabled=st.session_state.pipeline_running):
            run_full_pipeline(stages)
    
    with col2:
        if st.button("⏸️ Stop Pipeline", disabled=not st.session_state.pipeline_running):
            st.session_state.pipeline_running = False
            st.success("Pipeline stopped!")
    
    with col3:
        if st.button("🔄 Reset Progress"):
            st.session_state.current_stage = 0
            st.session_state.pipeline_running = False
            st.success("Progress reset!")
    
    # Progress bar
    progress_bar = st.progress(st.session_state.current_stage / len(stages))
    st.write(f"Progress: {st.session_state.current_stage}/{len(stages)} stages completed")
    
    # Individual stage controls
    st.markdown("---")
    st.subheader("🔧 Individual Stage Control")
    
    for i, (script, stage_name, description) in enumerate(stages):
        with st.expander(f"Stage {i+1}: {stage_name}", expanded=(i == st.session_state.current_stage)):
            
            # Show stage description and requirements
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Description:** {description}")
                st.write(f"**Script:** `{script}`")
                
                # Show file selection for stages that require it
                confirmed_file = None
                confirmed_equipment = None
                
                if stage_name.startswith("📊 P&ID Parsing"):
                    pid_files = [f for f in os.listdir("P&ID") if f.endswith('.cypher')] if os.path.exists("P&ID") else []
                    current_pid = st.session_state.current_pid_file or (pid_files[0] if pid_files else None)
                    confirmed_file = get_file_selection_confirmation(
                        "P&ID File", 
                        pid_files, 
                        current_pid,
                        "Select P&ID file for parsing"
                    )
                    
                elif stage_name.startswith("📖 Process Understanding"):
                    desc_files = [f for f in os.listdir("Process Description") if f.endswith('.txt')] if os.path.exists("Process Description") else []
                    current_desc = st.session_state.current_process_description or (desc_files[0] if desc_files else None)
                    confirmed_file = get_file_selection_confirmation(
                        "Process Description", 
                        desc_files, 
                        current_desc,
                        "Select process description file"
                    )
                    
                elif stage_name.startswith("🔍 HAZOP Analysis"):
                    equipment_list = get_equipment_from_db()
                    current_eq = st.session_state.current_equipment
                    current_eq_str = f"{current_eq['name']} ({current_eq['type']})" if current_eq else None
                    confirmed_equipment = get_equipment_selection_confirmation(equipment_list, current_eq_str)
            
            with col2:
                # Status indicator
                if i < st.session_state.current_stage:
                    st.success("✅ Completed")
                elif i == st.session_state.current_stage and st.session_state.pipeline_running:
                    st.warning("⏳ Running...")
                else:
                    st.info("⏸️ Pending")

                # Determine if this stage can run
                stage_can_run = True
                stage_requirements_met = True

                if stage_name.startswith("📊 P&ID Parsing"):
                    stage_can_run = confirmed_file is not None
                    stage_requirements_met = confirmed_file is not None
                elif stage_name.startswith("📖 Process Understanding"):
                    stage_can_run = confirmed_file is not None
                    stage_requirements_met = confirmed_file is not None
                elif stage_name.startswith("🔍 HAZOP Analysis"):
                    stage_can_run = confirmed_equipment is not None
                    stage_requirements_met = confirmed_equipment is not None

                if not stage_requirements_met:
                    st.error("❌ Requirements not met")

                # Run button
                if st.button(f"Run Stage {i+1}", key=f"run_stage_{i}", disabled=not stage_can_run or st.session_state.pipeline_running):
                    # Update session state with confirmed selections
                    if confirmed_file:
                        if stage_name.startswith("📊 P&ID Parsing"):
                            st.session_state.current_pid_file = confirmed_file
                        elif stage_name.startswith("📖 Process Understanding"):
                            st.session_state.current_process_description = confirmed_file

                    if confirmed_equipment:
                        st.session_state.current_equipment = confirmed_equipment

                    # Run the specific stage
                    run_single_stage(script, stage_name, i, stages)

            # --- Moved Human Checkpoint Here for Full-Width Display ---
            if stage_name == "📖 Process Understanding" and i == st.session_state.current_stage:
                if not st.session_state.desc_approved:
                    st.markdown("---") # Optional: adds a separator
                    # Show the full-page checkpoint interface
                    approval_status = show_human_checkpoint()
                    if approval_status:
                        st.success("✅ Human verification completed! Ready to continue.")
    
    # Execution log
    st.markdown("---")
    st.subheader("📋 Execution Log")
    
    if st.session_state.execution_log:
        for log in reversed(st.session_state.execution_log):
            timestamp = log['timestamp'].strftime("%H:%M:%S")
            stage = log['stage']
            status = log['status']
            
            if status == "completed":
                st.success(f"🟢 {timestamp} - {stage}: Completed ({log.get('execution_time', 0):.1f}s)")
                if 'output' in log and log['output']:
                    with st.expander("View Output"):
                        st.code(log['output'])
            elif status == "failed":
                st.error(f"🔴 {timestamp} - {stage}: Failed")
                if 'output' in log and log['output']:
                    with st.expander("View Error"):
                        st.code(log['output'])
            else:
                st.info(f"🟡 {timestamp} - {stage}: {status.title()}")
    else:
        st.info("No execution logs yet. Run a stage to see logs here.")

def run_full_pipeline(stages):
    """Run the complete pipeline with mandatory human checkpoint"""
    st.session_state.pipeline_running = True
    
    for i, (script, stage_name, description) in enumerate(stages):
        if i < st.session_state.current_stage:
            continue  # Skip already completed stages
            
        # Mandatory human checkpoint for "Process Understanding"
        if stage_name == "📖 Process Understanding" and not st.session_state.desc_approved:
            st.session_state.pipeline_paused_at = i
            st.warning("⏸️ Pipeline paused for mandatory human verification. Please approve the description below.")
            st.session_state.pipeline_running = False
            st.rerun() # Rerun to show the checkpoint UI
            return # Stop execution until user acts
        
        # Run the stage
        if st.session_state.pipeline_paused_at is None:
            # Prepare arguments based on stage, using confirmed selections
            args_list = []
            if stage_name.startswith("📊 P&ID Parsing"):
                if st.session_state.current_pid_file:
                    pid_path = os.path.join("P&ID", st.session_state.current_pid_file)
                    args_list = [pid_path]
            
            elif stage_name.startswith("📖 Process Understanding"):
                # Use the approved description file
                approved_desc_path = os.path.join("Process Description", "approved_description.txt")
                if os.path.exists(approved_desc_path):
                     args_list = ['--description-file', approved_desc_path]
                else:
                    st.error("❌ Approved description file not found! Cannot proceed.")
                    st.session_state.pipeline_running = False
                    break

            elif stage_name.startswith("🔍 HAZOP Analysis"):
                if st.session_state.current_equipment:
                    args_list = [st.session_state.current_equipment['name']]

            # Execute the script with arguments
            success, output, exec_time = run_pipeline_stage(script, stage_name, args_list)
            
            if success:
                st.session_state.current_stage = i + 1
                # Reset approval for the next run if needed, or handle as per logic
                if stage_name == "📖 Process Understanding":
                     st.session_state.desc_approved = False # Reset for future full runs
            else:
                st.error(f"❌ {stage_name} failed: {output}")
                st.session_state.pipeline_running = False
                break
            
            time.sleep(1)
            st.rerun()
    
    if st.session_state.current_stage >= len(stages):
        st.session_state.pipeline_running = False
        st.balloons()
        st.success("🎉 Pipeline completed successfully!")

def run_single_stage(script, stage_name, stage_index, stages):
    """Run a single pipeline stage"""
    st.session_state.pipeline_running = True
    
    # Prepare arguments based on stage
    args_list = []
    
    if stage_name.startswith("📊 P&ID Parsing"):
        if st.session_state.current_pid_file:
            pid_path = os.path.join("P&ID", st.session_state.current_pid_file)
            args_list = [pid_path]

    elif stage_name.startswith("📖 Process Understanding"):
        if st.session_state.current_process_description:
            desc_path = os.path.join("Process Description", st.session_state.current_process_description)
            # The argument must be in the format '--key', 'value'
            args_list = ['--description-file', desc_path]

    elif stage_name.startswith("🔍 HAZOP Analysis"):
        if st.session_state.current_equipment:
            args_list = [st.session_state.current_equipment['name']]
    
    # Run the stage
    success, output, exec_time = run_pipeline_stage(script, stage_name, args_list)
    
    if success:
        st.session_state.current_stage = stage_index + 1
        st.success(f"✅ {stage_name} completed in {exec_time:.1f}s")
    else:
        st.error(f"❌ {stage_name} failed: {output}")
    
    st.session_state.pipeline_running = False
    st.rerun()

def show_results():
    """Results viewing interface"""
    st.header("📊 Results & Reports")
    
    if not os.path.exists("Results"):
        st.info("No results generated yet. Run the pipeline first.")
        return
    
    # Get all result files
    result_files = [f for f in os.listdir("Results") if f.endswith(('.xlsx', '.json', '.txt'))]
    
    if not result_files:
        st.info("No result files found in Results directory.")
        return
    
    # Create tabs for different result types
    excel_files = [f for f in result_files if f.endswith('.xlsx')]
    json_files = [f for f in result_files if f.endswith('.json')]
    text_files = [f for f in result_files if f.endswith('.txt')]
    
    tabs = st.tabs([
        f"📊 Excel Reports ({len(excel_files)})",
        f"🔧 JSON Data ({len(json_files)})", 
        f"📝 Text Files ({len(text_files)})"
    ])
    
    with tabs[0]:
        if excel_files:
            for file in excel_files:
                with st.expander(f"📊 {file}"):
                    file_path = os.path.join("Results", file)
                    
                    try:
                        # Read Excel file
                        xl = pd.ExcelFile(file_path)
                        
                        # Show sheet names
                        st.write(f"**Sheets:** {', '.join(xl.sheet_names)}")
                        
                        # Show file info
                        file_info = get_file_info(file_path)
                        st.write(f"**Size:** {file_info['size']/1024:.1f} KB")
                        st.write(f"**Modified:** {file_info['modified'].strftime('%Y-%m-%d %H:%M')}")
                        
                        # Download button
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📥 Download {file}",
                                data=f,
                                file_name=file,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"download_excel_{file}"
                            )
                        
                        # Preview first sheet
                        df = pd.read_excel(file_path)
                        st.write(f"**Preview of {xl.sheet_names[0]}:**")
                        st.dataframe(df.head(10))
                        
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
        else:
            st.info("No Excel files found.")
    
    with tabs[1]:
        if json_files:
            for file in json_files:
                with st.expander(f"🔧 {file}"):
                    file_path = os.path.join("Results", file)
                    
                    try:
                        # Read JSON file
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Show file info
                        file_info = get_file_info(file_path)
                        st.write(f"**Size:** {file_info['size']/1024:.1f} KB")
                        st.write(f"**Modified:** {file_info['modified'].strftime('%Y-%m-%d %H:%M')}")
                        
                        # Download button
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📥 Download {file}",
                                data=f,
                                file_name=file,
                                mime="application/json",
                                key=f"download_json_{file}"
                            )
                        
                        # Show JSON structure
                        st.write("**Data Structure:**")
                        st.json(data, expanded=False)
                        
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
        else:
            st.info("No JSON files found.")
    
    with tabs[2]:
        if text_files:
            for file in text_files:
                with st.expander(f"📝 {file}"):
                    file_path = os.path.join("Results", file)
                    
                    try:
                        # Read text file
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        # Show file info
                        file_info = get_file_info(file_path)
                        st.write(f"**Size:** {file_info['size']/1024:.1f} KB")
                        st.write(f"**Modified:** {file_info['modified'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Lines:** {len(content.splitlines())}")
                        
                        # Download button
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📥 Download {file}",
                                data=f,
                                file_name=file,
                                mime="text/plain",
                                key=f"download_text_{file}"
                            )
                        
                        # Show content preview
                        st.write("**Content Preview:**")
                        st.code(content[:2000] + ("..." if len(content) > 2000 else ""))
                        
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
        else:
            st.info("No text files found.")
    
    # Summary statistics
    st.markdown("---")
    st.subheader("📈 Summary Statistics")
    
    if excel_files:
        # Try to find the main HAZOP report
        hazop_files = [f for f in excel_files if 'hazop' in f.lower() or 'report' in f.lower()]
        
        if hazop_files:
            main_file = hazop_files[0]
            file_path = os.path.join("Results", main_file)
            
            try:
                df = pd.read_excel(file_path)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Records", len(df))
                
                with col2:
                    if 'Risk Level' in df.columns:
                        high_risk = len(df[df['Risk Level'].str.contains('high', case=False, na=False)])
                        st.metric("High Risk Items", high_risk)
                
                with col3:
                    if 'Equipment' in df.columns:
                        unique_equipment = df['Equipment'].nunique()
                        st.metric("Unique Equipment", unique_equipment)
                
                with col4:
                    if 'Deviation' in df.columns:
                        unique_deviations = df['Deviation'].nunique()
                        st.metric("Unique Deviations", unique_deviations)
                
                # Show risk distribution if available
                if 'Risk Level' in df.columns:
                    st.markdown("### 🎯 Risk Level Distribution")
                    risk_counts = df['Risk Level'].value_counts()
                    
                    fig = px.pie(
                        values=risk_counts.values,
                        names=risk_counts.index,
                        title="Risk Level Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f"Could not analyze report: {e}")

def show_configuration():
    """Configuration interface"""
    st.header("⚙️ System Configuration")
    
    # Configuration status
    st.subheader("🔧 Configuration Status")
    
    config_checks = [
        ("Gemini API Key", hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY != 'your_gemini_api_key_here'),
        ("Neo4j URI", hasattr(config, 'NEO4J_URI') and config.NEO4J_URI != 'your_neo4j_uri_here'),
        ("Neo4j Username", hasattr(config, 'NEO4J_USERNAME') and config.NEO4J_USERNAME != 'your_neo4j_username_here'),
        ("Neo4j Password", hasattr(config, 'NEO4J_PASSWORD') and config.NEO4J_PASSWORD != 'your_neo4j_password_here'),
        ("P&ID Path", hasattr(config, 'PID_PATH') and os.path.exists(getattr(config, 'PID_PATH', ''))),
    ]
    
    all_valid = True
    for check_name, is_valid in config_checks:
        if is_valid:
            st.success(f"✅ {check_name}")
        else:
            st.error(f"❌ {check_name}")
            all_valid = False
    
    if all_valid:
        st.session_state.config_validated = True
        st.success("🎉 All configurations are valid!")
    else:
        st.session_state.config_validated = False
        st.error("⚠️ Please fix configuration issues before running the pipeline.")
    
    st.markdown("---")
    
    # Configuration editor
    st.subheader("📝 Configuration Editor")
    
    if os.path.exists('config.py'):
        with open('config.py', 'r') as f:
            config_content = f.read()
        
        edited_config = st.text_area(
            "Edit configuration:",
            value=config_content,
            height=400,
            key="config_editor"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Configuration"):
                try:
                    with open('config.py', 'w') as f:
                        f.write(edited_config)
                    st.success("Configuration saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving configuration: {e}")
        
        with col2:
            if st.button("🔄 Reload Original"):
                st.rerun()
    
    # System information
    st.markdown("---")
    st.subheader("💻 System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📁 Directory Structure")
        
        directories = {
            "P&ID": "P&ID",
            "MSDS": "MSDS",
            "Context": "Context for RAG", 
            "Process Description": "Process Description",
            "Results": "Results"
        }
        
        for display_name, directory in directories.items():
            if os.path.exists(directory):
                file_count = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
                total_size = sum(os.path.getsize(os.path.join(directory, f)) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)))
                
                st.write(f"**{display_name}:** {file_count} files, {total_size/1024:.1f} KB")
            else:
                st.write(f"**{display_name}:** ❌ Not found")
    
    with col2:
        st.markdown("### 🔄 Recent Activity")
        
        if st.session_state.execution_log:
            recent_logs = st.session_state.execution_log[-3:]
            for log in reversed(recent_logs):
                timestamp = log['timestamp'].strftime("%H:%M:%S")
                stage = log['stage']
                status = log['status']
                
                if status == "completed":
                    st.success(f"🟢 {timestamp} - {stage}")
                elif status == "failed":
                    st.error(f"🔴 {timestamp} - {stage}")
                else:
                    st.info(f"🟡 {timestamp} - {stage}")
        else:
            st.info("No recent activity")

if __name__ == "__main__":
    main()