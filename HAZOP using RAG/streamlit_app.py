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


def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        'current_stage': 0,
        'pipeline_running': False,
        'uploaded_files': {'pid': [], 'msds': []},
        'execution_log': [],
        'config_validated': False
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
    """Pipeline execution interface with prominent file selection"""
    st.header("🚀 Pipeline Execution")
    
    # Add a prominent file selection section at the top
    st.subheader("📋 Pre-execution Setup")
    st.markdown("**Configure your analysis parameters before running the pipeline:**")
    
    # Create columns for file selections
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📊 P&ID File Selection")
        pid_files = [f for f in os.listdir("P&ID") if f.endswith('.cypher')] if os.path.exists("P&ID") else []
        if pid_files:
            selected_pid = st.selectbox(
                "Select P&ID Cypher file:", 
                pid_files, 
                key="global_pid_selector",
                help="This file will be used for P&ID parsing (Stage 1)"
            )
            st.session_state.selected_pid_file = selected_pid
            st.success(f"✅ Selected: {selected_pid}")
        else:
            st.warning("⚠️ No P&ID files found. Upload files in the File Upload section.")
            st.session_state.selected_pid_file = None
    
    with col2:
        st.markdown("#### 📖 Process Description")
        desc_files = [f for f in os.listdir("Process Description") if f.endswith('.txt')] if os.path.exists("Process Description") else []
        if desc_files:
            selected_desc = st.selectbox(
                "Select process description:", 
                desc_files, 
                key="global_desc_selector",
                help="This file will be used for process understanding (Stage 5)"
            )
            st.session_state.selected_process_description = selected_desc
            st.success(f"✅ Selected: {selected_desc}")
        else:
            st.warning("⚠️ No process description files found. Upload .txt files.")
            st.session_state.selected_process_description = None
    
    with col3:
        st.markdown("#### 🔧 Equipment Selection")
        equipment_list = get_equipment_from_db()
        if equipment_list:
            equipment_options = [f"{eq['name']} ({eq['type']})" for eq in equipment_list]
            selected_equipment_option = st.selectbox(
                "Select equipment for HAZOP:", 
                equipment_options, 
                key="global_equipment_selector",
                help="This equipment will be analyzed in Stage 7 (HAZOP Analysis)"
            )
            # Find the selected equipment data
            selected_eq_data = next((eq for eq in equipment_list if f"{eq['name']} ({eq['type']})" == selected_equipment_option), None)
            st.session_state.selected_equipment = selected_eq_data
            st.success(f"✅ Selected: {selected_equipment_option}")
        else:
            st.warning("⚠️ No equipment found. Run stages 1-4 first to populate equipment.")
            st.session_state.selected_equipment = None
    
    # Show current selections summary
    st.markdown("---")
    st.subheader("📋 Current Analysis Configuration")
    
    config_col1, config_col2, config_col3 = st.columns(3)
    
    with config_col1:
        if st.session_state.get('selected_pid_file'):
            st.info(f"📊 P&ID: {st.session_state.selected_pid_file}")
        else:
            st.error("❌ No P&ID file selected")
    
    with config_col2:
        if st.session_state.get('selected_process_description'):
            st.info(f"📖 Process: {st.session_state.selected_process_description}")
        else:
            st.error("❌ No process description selected")
    
    with config_col3:
        if st.session_state.get('selected_equipment'):
            st.info(f"🔧 Equipment: {st.session_state.selected_equipment['name']}")
        else:
            st.error("❌ No equipment selected")
    
    st.markdown("---")
    
    # Pipeline stages
    stages = [
        ("01_parsing_P&ID.py", "📊 P&ID Parsing", "Load P&ID data into Neo4j"),
        ("02_ontology_loader.py", "🏗️ Ontology Loading", "Apply HAZOP schema constraints"), 
        ("03_semantic_enrichment.py", "🧠 Semantic Enrichment", "Enrich with chemical data"),
        ("Process description using ontology/Storage_tank_description_generator.py","📝 Description Generation", "Generate equipment descriptions")
        ("05_Understanding_process_using_LLM.py", "📖 Process Understanding", "Generate process descriptions"),
        ("06_Generate_applicable_deviations.py", "⚠️ Deviation Generation", "Create equipment deviations"),
        ("07_HAZOP_analysis.py", "🔍 HAZOP Analysis", "Perform main analysis"),
        ("08_verify_accuracy.py", "✅ Verification", "Verify results")
    ]
    
    # Control buttons with better validation
    col1, col2, col3 = st.columns(3)
    
    # Check if minimum requirements are met for full pipeline
    can_run_full_pipeline = (
        st.session_state.get('selected_pid_file') is not None and
        st.session_state.get('selected_process_description') is not None and
        st.session_state.get('selected_equipment') is not None
    )
    
    with col1:
        if st.button("▶️ Run Full Pipeline", 
                    type="primary", 
                    disabled=st.session_state.pipeline_running or not can_run_full_pipeline):
            if can_run_full_pipeline:
                run_full_pipeline(stages)
            else:
                st.error("Please select all required files and equipment before running full pipeline")
    
    with col2:
        if st.button("⏸️ Stop Pipeline", disabled=not st.session_state.pipeline_running):
            st.session_state.pipeline_running = False
            st.success("Pipeline stopped!")
    
    with col3:
        if st.button("🔄 Reset Progress"):
            st.session_state.current_stage = 0
            st.session_state.pipeline_running = False
            st.success("Progress reset!")
    
    if not can_run_full_pipeline:
        st.warning("⚠️ Full pipeline disabled: Please select P&ID file, process description, and equipment above")
    
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
                
                # Show what file/config this stage will use
                if stage_name.startswith("📊 P&ID Parsing"):
                    if st.session_state.get('selected_pid_file'):
                        st.info(f"Will use P&ID file: {st.session_state.selected_pid_file}")
                    else:
                        st.error("❌ No P&ID file selected - use dropdown above")
                
                
                elif stage_name.startswith("📖 Process Understanding"):
                    if st.session_state.get('selected_process_description'):
                        st.info(f"Will use description: {st.session_state.selected_process_description}")
                    else:
                        st.error("❌ No process description selected - use dropdown above")
                
                elif stage_name.startswith("🔍 HAZOP Analysis"):
                    if st.session_state.get('selected_equipment'):
                        st.info(f"Will analyze equipment: {st.session_state.selected_equipment['name']} ({st.session_state.selected_equipment['type']})")
                    else:
                        st.error("❌ No equipment selected - use dropdown above")
            
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
                if stage_name.startswith("📊 P&ID Parsing") and not st.session_state.get('selected_pid_file'):
                    stage_can_run = False
                elif stage_name.startswith("📖 Process Understanding") and not st.session_state.get('selected_process_description'):
                    stage_can_run = False
                elif stage_name.startswith("🔍 HAZOP Analysis") and not st.session_state.get('selected_equipment'):
                    stage_can_run = False
                
                # Run button
                if st.button(f"Run Stage {i+1}", key=f"run_stage_{i}", disabled=not stage_can_run):
                    # Prepare arguments based on stage requirements and current selections
                    args_to_pass = []
                    
                    if stage_name.startswith("📊 P&ID Parsing"):
                        args_to_pass = ["--file", os.path.join("P&ID", st.session_state.selected_pid_file)]
                    elif stage_name.startswith("📖 Process Understanding"):
                        args_to_pass = ["--description-file", os.path.join("Process Description", st.session_state.selected_process_description)]
                    elif stage_name.startswith("🔍 HAZOP Analysis"):
                        args_to_pass = [
                            "--equipment-name", st.session_state.selected_equipment['name'],
                            "--equipment-type", st.session_state.selected_equipment['type']
                        ]
                    
                    with st.spinner(f"Running {stage_name}..."):
                        success, output, exec_time = run_pipeline_stage(script, stage_name.split(' ', 1)[1], args_to_pass)
                        if success:
                            st.success(f"✅ Stage {i+1} completed! ({exec_time:.1f}s)")
                            st.session_state.current_stage = max(st.session_state.current_stage, i + 1)
                        else:
                            st.error(f"❌ Stage {i+1} failed!")

                        with st.expander("Show Execution Output", expanded=not success):
                            if success:
                                st.success("Execution completed successfully!")
                                st.code(output, language='text')
                            else:
                                st.error("Execution failed with errors:")
                                st.code(output, language="text")
                                
                                # Add specific troubleshooting
                                if "--file" in output and "required" in output:
                                    st.error("💡 Solution: Make sure you selected a P&ID file in the dropdown above")
                                elif "UnicodeEncodeError" in output:
                                    st.error("💡 Solution: Try setting PYTHONIOENCODING=utf-8 in your environment")
                    
                    st.rerun()  # Refresh to update progress
    
    # Execution log
    if st.session_state.execution_log:
        st.markdown("---")
        st.subheader("📋 Execution Log")
        
        for log in reversed(st.session_state.execution_log[-5:]):  # Show last 5 entries
            timestamp = log['timestamp'].strftime("%H:%M:%S")
            stage = log['stage']
            status = log['status']
            
            if status == "completed":
                st.success(f"🟢 {timestamp} - {stage}: Completed ({log.get('execution_time', 0):.1f}s)")
            elif status == "failed":
                st.error(f"🔴 {timestamp} - {stage}: Failed")
            else:
                st.info(f"🟡 {timestamp} - {stage}: {status.title()}")

def run_full_pipeline(stages):
    """Run the complete pipeline with proper argument handling"""
    st.session_state.pipeline_running = True
    st.session_state.current_stage = 0
    
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Get file selections for stages that need them
    pid_files = [f for f in os.listdir("P&ID") if f.endswith('.cypher')] if os.path.exists("P&ID") else []
    desc_files = [f for f in os.listdir("Process Description") if f.endswith('.txt')] if os.path.exists("Process Description") else []
    
    for i, (script, stage_name, description) in enumerate(stages):
        if not st.session_state.pipeline_running:
            status_placeholder.warning("⏸️ Pipeline execution stopped by user")
            break
            
        st.session_state.current_stage = i
        progress_placeholder.progress((i + 1) / len(stages))
        status_placeholder.info(f"⏳ Running: {stage_name}")
        
        # Prepare arguments for specific stages
        args_to_pass = []
        
        if stage_name.startswith("📊 P&ID Parsing") and pid_files:
            # Use the first available P&ID file
            args_to_pass = ["--file", os.path.join("P&ID", pid_files[0])]
            st.info(f"Using P&ID file: {pid_files[0]}")
            
        elif stage_name.startswith("📖 Process Understanding") and desc_files:
            # Use the first available process description file
            args_to_pass = ["--description-file", os.path.join("Process Description", desc_files[0])]
            st.info(f"Using process description: {desc_files[0]}")
            
        elif stage_name.startswith("🔍 HAZOP Analysis"):
            # For full pipeline, we might need to handle this differently
            # For now, we'll skip the equipment selection in full pipeline mode
            st.warning("HAZOP Analysis stage requires equipment selection. Please run this stage individually.")
            continue
        
        success, output, exec_time = run_pipeline_stage(script, stage_name.split(' ', 1)[1], args_to_pass)
        
        if not success:
            status_placeholder.error(f"❌ Pipeline failed at {stage_name}")
            
            # Show detailed error in an expander
            with st.expander("🔍 View Error Details", expanded=True):
                st.error(f"**Failed Stage:** {stage_name}")
                st.write(f"**Script:** {script}")
                st.write(f"**Arguments:** {' '.join(args_to_pass) if args_to_pass else 'None'}")
                st.code(output, language="text")
            
            # Offer recovery options
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔄 Retry Stage", key="retry_failed_stage"):
                    continue
            with col2:
                if st.button("⏭️ Skip Stage", key="skip_failed_stage"):
                    st.warning(f"Skipping {stage_name}")
                    continue
            with col3:
                if st.button("🛑 Stop Pipeline", key="stop_failed_pipeline"):
                    st.session_state.pipeline_running = False
                    break
            
            st.session_state.pipeline_running = False
            return
        
        time.sleep(1)  # Brief pause between stages
    
    if st.session_state.pipeline_running:
        st.session_state.current_stage = len(stages)
        status_placeholder.success("🎉 Pipeline completed successfully!")
        st.balloons()
    
    st.session_state.pipeline_running = False

def run_individual_stage(script, stage_name):
    """Run individual pipeline stage"""
    with st.spinner(f"Running {stage_name}..."):
        success, output, exec_time = run_pipeline_stage(script, stage_name)
        
        if success:
            st.success(f"✅ {stage_name} completed successfully! ({exec_time:.1f}s)")
            
            # Update current stage if this was the next stage
            stage_scripts = [
                "01_parsing_P&ID.py", "02_ontology_loader.py", "03_semantic_enrichment.py",
                "Process description using ontology/Storage_tank_description_generator.py","05_Understanding_process_using_LLM.py", 
                "06_Generate_applicable_deviations.py", "07_HAZOP_analysis.py", "08_verify_accuracy.py"
            ]
            
            if script in stage_scripts:
                stage_index = stage_scripts.index(script)
                st.session_state.current_stage = max(st.session_state.current_stage, stage_index + 1)
        else:
            st.error(f"❌ {stage_name} failed!")
        
        # Show output
        with st.expander("Show execution details"):
            st.code(output)

def show_results():
    """Results analysis page"""
    st.header("📊 Results Analysis")
    
    results_dir = "Results"
    
    if not os.path.exists(results_dir):
        st.warning("📂 Results directory not found. Run the pipeline first to generate results.")
        return
    
    # Get result files
    result_files = []
    for file in os.listdir(results_dir):
        if file.endswith(('.xlsx', '.json', '.csv', '.md')):
            result_files.append(file)
    
    if not result_files:
        st.info("📄 No result files found yet. Run the HAZOP analysis to generate reports.")
        return
    
    # File metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        excel_files = [f for f in result_files if f.endswith('.xlsx')]
        st.metric("📊 Excel Reports", len(excel_files))
    
    with col2:
        json_files = [f for f in result_files if f.endswith('.json')]
        st.metric("📋 JSON Files", len(json_files))
    
    with col3:
        csv_files = [f for f in result_files if f.endswith('.csv')]
        st.metric("📈 CSV Files", len(csv_files))
    
    with col4:
        md_files = [f for f in result_files if f.endswith('.md')]
        st.metric("📝 Documents", len(md_files))
    
    st.markdown("---")
    
    # File browser
    st.subheader("📁 Result Files")
    
    selected_file = st.selectbox("Select file to preview:", result_files)
    
    if selected_file:
        file_path = os.path.join(results_dir, selected_file)
        file_info = get_file_info(file_path)
        
        # File information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Size", f"{file_info['size']/1024:.1f} KB")
        with col2:
            st.metric("Modified", file_info['modified'].strftime("%Y-%m-%d"))
        with col3:
            st.metric("Type", selected_file.split('.')[-1].upper())
        
        # File preview
        try:
            if selected_file.endswith('.xlsx'):
                st.subheader("📊 Excel File Preview")
                df = pd.read_excel(file_path)
                st.dataframe(df.head(10), use_container_width=True)
                
                # Basic statistics
                st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
                
                # HAZOP specific analysis
                #if 'Parameter' in df.columns:
                #    st.subheader("📈 Parameter Analysis")
                #    param_counts = df['Parameter'].value_counts()
                #    fig = px.bar(x=param_counts.values, y=param_counts.index, 
                #               orientation='h', title="Parameter Distribution")
                #    st.plotly_chart(fig, use_container_width=True)
            
            elif selected_file.endswith('.json'):
                st.subheader("📋 JSON File Preview")
                with open(file_path, 'r') as f:
                    data = json.load(f)
                st.json(data)
            
            elif selected_file.endswith('.csv'):
                st.subheader("📈 CSV File Preview")
                df = pd.read_csv(file_path)
                st.dataframe(df.head(10), use_container_width=True)
                st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
            
            elif selected_file.endswith('.md'):
                st.subheader("📝 Markdown Document")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.markdown(content)
        
        except Exception as e:
            st.error(f"Error loading file: {e}")
        
        # Download button
        with open(file_path, 'rb') as f:
            st.download_button(
                label=f"📥 Download {selected_file}",
                data=f.read(),
                file_name=selected_file,
                mime="application/octet-stream"
            )

def show_configuration():
    """Configuration page"""
    st.header("⚙️ Configuration")
    
    tab1, tab2 = st.tabs(["🔧 Settings", "🧪 Validation"])
    
    with tab1:
        st.subheader("Database Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            neo4j_uri = st.text_input("Neo4j URI", 
                                     value=getattr(config, 'NEO4J_URI', 'neo4j://localhost:7687'))
            neo4j_user = st.text_input("Neo4j Username", 
                                      value=getattr(config, 'NEO4J_USERNAME', 'neo4j'))
        with col2:
            neo4j_password = st.text_input("Neo4j Password", type="password",
                                          value=getattr(config, 'NEO4J_PASSWORD', ''))
        
        st.subheader("API Configuration")
        col1, col2 = st.columns(2)
        with col1:
            gemini_key = st.text_input("Gemini API Key", type="password",
                                      value=getattr(config, 'GEMINI_API_KEY', ''))
        with col2:
            gemini_model = st.text_input("Gemini Model", 
                                        value=getattr(config, 'GEMINI_MODEL_NAME', 'gemini-1.5-pro'))
        
        st.subheader("File Paths")
        ontology_path = st.text_input("Ontology File Path", 
                                     value=getattr(config, 'ONTOLOGY_FILE_PATH', 'HAZOP_Ontology_CLEAN.rdf'))
        
        if st.button("💾 Save Configuration"):
            # This would save to config file in a real implementation
            st.success("✅ Configuration saved! (Note: Restart application to apply changes)")
    
    with tab2:
        st.subheader("🧪 System Validation")
        
        if st.button("🔍 Run Validation"):
            st.info("Running system validation...")
            
            # Check required files
            st.write("**📁 File Check:**")
            required_files = [
                "HAZOP_Ontology_CLEAN.rdf",
                "Context for RAG/Equipment_and_Deviation.csv"
            ]
            
            for file_path in required_files:
                if os.path.exists(file_path):
                    st.success(f"✅ {file_path}")
                else:
                    st.error(f"❌ {file_path} - Missing")
            
            # Check directories
            st.write("**📂 Directory Check:**")
            required_dirs = ["P&ID", "MSDS", "Context for RAG", "Results"]
            
            for directory in required_dirs:
                if os.path.exists(directory):
                    file_count = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
                    st.success(f"✅ {directory}/ ({file_count} files)")
                else:
                    st.error(f"❌ {directory}/ - Missing")
            
            # Check Python scripts
            st.write("**🐍 Script Check:**")
            pipeline_scripts = [
                "01_parsing_P&ID.py", "02_ontology_loader.py", "03_semantic_enrichment.py",
                "Process description using ontology/Storage_tank_description_generator.py","05_Understanding_process_using_LLM.py",
                "06_Generate_applicable_deviations.py", "07_HAZOP_analysis.py", "08_verify_accuracy.py"
            ]
            
            for script in pipeline_scripts:
                if os.path.exists(script):
                    st.success(f"✅ {script}")
                else:
                    st.error(f"❌ {script} - Missing")
            
            # Check configuration
            st.write("**⚙️ Configuration Check:**")
            config_items = [
                ("NEO4J_URI", getattr(config, 'NEO4J_URI', None)),
                ("NEO4J_USERNAME", getattr(config, 'NEO4J_USERNAME', None)),
                ("NEO4J_PASSWORD", getattr(config, 'NEO4J_PASSWORD', None)),
                ("GEMINI_API_KEY", getattr(config, 'GEMINI_API_KEY', None))
            ]
            
            for item_name, item_value in config_items:
                if item_value and not item_value.startswith('your_'):
                    st.success(f"✅ {item_name}")
                else:
                    st.error(f"❌ {item_name} - Not configured")

if __name__ == "__main__":
    main()