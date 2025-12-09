"""
Advanced Process Flow Diagram Generator
Supports enhanced process mapping with automation potential, risk indicators, SLA, and more
"""

import streamlit as st
import pandas as pd
import graphviz
from typing import Dict, Tuple, Optional
import io

# Page configuration
st.set_page_config(
    page_title="Advanced Process Flow Diagram",
    page_icon="📊",
    layout="wide"
)

# Step type configurations with professional styling
STEP_CONFIGS = {
    'process': {'shape': 'box', 'style': 'filled', 'fillcolor': '#90EE90', 'color': 'black', 'penwidth': '2'},
    'decision': {'shape': 'diamond', 'style': 'filled', 'fillcolor': '#FFD700', 'color': 'black', 'penwidth': '2'},
    'manual': {'shape': 'box', 'style': 'filled', 'fillcolor': '#BA8FD8', 'color': 'black', 'penwidth': '2'},
    'predefined': {'shape': 'box3d', 'style': 'filled', 'fillcolor': '#4682B4', 'color': 'black', 'fontcolor': 'white', 'penwidth': '2'},
    'pause': {'shape': 'hexagon', 'style': 'filled,dashed', 'fillcolor': '#FF8C00', 'color': 'black', 'penwidth': '2'},
    'input': {'shape': 'invtrapezium', 'style': 'filled', 'fillcolor': '#87CEEB', 'color': 'black', 'penwidth': '2'},
    'output': {'shape': 'trapezium', 'style': 'filled', 'fillcolor': '#87CEEB', 'color': 'black', 'penwidth': '2'},
    'form': {'shape': 'note', 'style': 'filled,dashed', 'fillcolor': '#D3D3D3', 'color': 'black', 'penwidth': '2'},
    'end': {'shape': 'oval', 'style': 'filled', 'fillcolor': '#FF0000', 'color': 'black', 'fontcolor': 'white', 'penwidth': '2'}
}

def validate_columns(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate DataFrame contains all REQUIRED columns.
    Optional columns are allowed but not required.
    """
    required_columns = [
        'ProcessName', 'ProcessID', 'Lane', 'SystemUsed', 'StepID', 
        'StepOrder', 'StepLabel', 'StepType', 'NextStep', 
        'YesNext', 'NoNext'
    ]
    
    optional_columns = [
        'Trigger', 'FinalOutput', 'SLA', 'AutomationPotential',
        'ProcessRisk', 'ControlDescription', 'RelatedDocuments', 'Notes'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    # Log which optional columns are present
    present_optional = [col for col in optional_columns if col in df.columns]
    
    return True, f"✓ All required columns present. Optional columns found: {', '.join(present_optional) if present_optional else 'None'}"

def get_step_attributes(step_type: str, automation_potential: Optional[str] = None, 
                        process_risk: Optional[str] = None) -> Dict[str, str]:
    """
    Get visual attributes for a step, with enhancements based on automation potential and risk.
    
    AutomationPotential = 'Yes' → Dashed border
    ProcessRisk = 'High' → Red border
    """
    step_type_lower = step_type.lower().strip()
    attrs = STEP_CONFIGS.get(step_type_lower, STEP_CONFIGS['process']).copy()
    
    # Apply automation potential styling (dashed border)
    if automation_potential and str(automation_potential).strip().lower() in ['yes', 'y', 'true', '1']:
        attrs['style'] = 'filled,dashed'
        attrs['penwidth'] = '3'
    
    # Apply high risk styling (red border)
    if process_risk and str(process_risk).strip().lower() == 'high':
        attrs['color'] = 'red'
        attrs['penwidth'] = '3'
    
    return attrs

def format_node_label(step_label: str, system_used: Optional[str] = None, 
                     sla: Optional[str] = None) -> str:
    """
    Format node label to include step name, system, and SLA if present.
    
    Format:
    ┌──────────────────┐
    │   Step Label     │
    │   [System]       │
    │   ⏱ SLA: 2hrs   │
    └──────────────────┘
    """
    label_parts = [step_label]
    
    # Add system if present
    if system_used and str(system_used).strip() and str(system_used).strip().lower() != 'nan':
        label_parts.append(f"[{system_used}]")
    
    # Add SLA if present
    if sla and str(sla).strip() and str(sla).strip().lower() != 'nan':
        label_parts.append(f"⏱ {sla}")
    
    return "\\n".join(label_parts)

def build_flow_for_process(df_proc: pd.DataFrame, process_name: str, 
                          orientation: str = 'LR') -> graphviz.Digraph:
    """
    Build enhanced Graphviz flowchart with swimlanes, annotations, and advanced features.
    
    Features:
    - SystemUsed displayed in nodes
    - Trigger shown at diagram start
    - FinalOutput shown near end
    - SLA displayed in nodes
    - AutomationPotential: dashed borders
    - ProcessRisk=High: red borders
    """
    # Create main graph
    dot = graphviz.Digraph(comment=process_name)
    dot.attr(rankdir=orientation, splines='polyline', nodesep='1.0', ranksep='1.5')
    dot.attr('node', fontname='Arial', fontsize='11', margin='0.3')
    dot.attr('edge', fontname='Arial', fontsize='10', color='black', penwidth='1.5')
    
    # Add process title header
    dot.attr(label=process_name, labelloc='t', labeljust='l', fontsize='16', fontname='Arial Bold')
    
    # Sort by StepOrder
    df_sorted = df_proc.sort_values('StepOrder').reset_index(drop=True)
    
    # Get trigger and final output for annotations
    trigger = None
    final_output = None
    
    if 'Trigger' in df_sorted.columns:
        triggers = df_sorted['Trigger'].dropna().unique()
        if len(triggers) > 0 and str(triggers[0]).strip().lower() != 'nan':
            trigger = str(triggers[0])
    
    if 'FinalOutput' in df_sorted.columns:
        outputs = df_sorted['FinalOutput'].dropna().unique()
        if len(outputs) > 0 and str(outputs[0]).strip().lower() != 'nan':
            final_output = str(outputs[0])
    
    # Add trigger annotation at the start (invisible node with label)
    if trigger:
        dot.node('_trigger', f'▶ TRIGGER: {trigger}', 
                shape='plaintext', fontsize='12', fontcolor='blue', fontname='Arial Bold')
    
    # Add final output annotation (will connect to end node)
    if final_output:
        dot.node('_finaloutput', f'✓ OUTPUT: {final_output}', 
                shape='plaintext', fontsize='12', fontcolor='green', fontname='Arial Bold')
    
    # Group steps by lane
    lanes = df_sorted['Lane'].unique()
    lane_steps = {lane: df_sorted[df_sorted['Lane'] == lane] for lane in lanes}
    
    # Create swimlanes as subgraphs
    for idx, lane in enumerate(lanes):
        with dot.subgraph(name=f'cluster_{idx}') as cluster:
            cluster.attr(
                label=str(lane), 
                style='filled', 
                color='black',
                fillcolor='#E8E8E8',
                fontsize='14',
                fontname='Arial Bold',
                labeljust='l',
                penwidth='2'
            )
            
            # Add nodes for this lane
            lane_df = lane_steps[lane]
            for _, row in lane_df.iterrows():
                step_id = str(row['StepID'])
                step_label = str(row['StepLabel'])
                step_type = str(row['StepType'])
                
                # Get optional fields
                system_used = row.get('SystemUsed')
                sla = row.get('SLA')
                automation_potential = row.get('AutomationPotential')
                process_risk = row.get('ProcessRisk')
                
                # Get attributes with risk/automation enhancements
                attrs = get_step_attributes(step_type, automation_potential, process_risk)
                
                # Format label with system and SLA
                formatted_label = format_node_label(step_label, system_used, sla)
                
                # Add the node
                cluster.node(step_id, formatted_label, **attrs)
    
    # Connect trigger to first step if present
    if trigger and len(df_sorted) > 0:
        first_step = str(df_sorted.iloc[0]['StepID'])
        dot.edge('_trigger', first_step, style='dotted', color='blue')
    
    # Add edges (connections between steps)
    end_nodes = []  # Track end nodes to connect to final output
    
    for _, row in df_sorted.iterrows():
        step_id = str(row['StepID'])
        step_type = str(row['StepType']).lower().strip()
        current_lane = str(row['Lane'])
        
        # Track if this is an end node
        is_end_node = step_type == 'end'
        
        # Handle decision nodes with Yes/No branches
        if step_type == 'decision':
            yes_next = str(row['YesNext'])
            no_next = str(row['NoNext'])
            
            if pd.notna(row['YesNext']) and yes_next != 'nan' and yes_next != '':
                # Check if cross-lane connection
                target_row = df_sorted[df_sorted['StepID'] == yes_next]
                if not target_row.empty:
                    target_lane = str(target_row.iloc[0]['Lane'])
                    if target_lane != current_lane:
                        dot.edge(step_id, yes_next, label='Yes', color='green', fontcolor='green', 
                                style='dashed', penwidth='1.5', arrowhead='normal')
                    else:
                        dot.edge(step_id, yes_next, label='Yes', color='green', fontcolor='green',
                                penwidth='1.5', arrowhead='normal')
            
            if pd.notna(row['NoNext']) and no_next != 'nan' and no_next != '':
                # Check if cross-lane connection
                target_row = df_sorted[df_sorted['StepID'] == no_next]
                if not target_row.empty:
                    target_lane = str(target_row.iloc[0]['Lane'])
                    if target_lane != current_lane:
                        dot.edge(step_id, no_next, label='No', color='red', fontcolor='red',
                                style='dashed', penwidth='1.5', arrowhead='normal')
                    else:
                        dot.edge(step_id, no_next, label='No', color='red', fontcolor='red',
                                penwidth='1.5', arrowhead='normal')
        else:
            # Normal flow using NextStep
            next_step = str(row['NextStep'])
            if pd.notna(row['NextStep']) and next_step != 'nan' and next_step != '':
                # Check if cross-lane connection
                target_row = df_sorted[df_sorted['StepID'] == next_step]
                if not target_row.empty:
                    target_lane = str(target_row.iloc[0]['Lane'])
                    if target_lane != current_lane:
                        dot.edge(step_id, next_step, style='dashed', penwidth='1.5', arrowhead='normal')
                    else:
                        dot.edge(step_id, next_step, penwidth='1.5', arrowhead='normal')
            elif is_end_node:
                # This is an end node with no next step
                end_nodes.append(step_id)
    
    # Connect end nodes to final output annotation
    if final_output and end_nodes:
        for end_node in end_nodes:
            dot.edge(end_node, '_finaloutput', style='dotted', color='green')
    
    return dot

def create_sample_data() -> pd.DataFrame:
    """Create comprehensive sample data demonstrating all features."""
    sample_data = {
        'ProcessName': ['Employee Onboarding'] * 8,
        'ProcessID': ['P-ONB-001'] * 8,
        'Lane': ['HR', 'HR', 'IT', 'IT', 'IT', 'Manager', 'Manager', 'HR'],
        'SystemUsed': ['WorkDay', 'WorkDay', 'Active Directory', 'ServiceNow', 'ServiceNow', 'Email', 'Outlook', 'WorkDay'],
        'Trigger': ['New hire acceptance email', '', '', '', '', '', '', ''],
        'FinalOutput': ['', '', '', '', '', '', '', 'Employee fully onboarded'],
        'StepID': ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'],
        'StepOrder': [1, 2, 3, 4, 5, 6, 7, 8],
        'StepLabel': [
            'Create HR profile',
            'Verify documents',
            'Create AD account',
            'Assign equipment',
            'Setup access',
            'Review onboarding',
            'Schedule 1:1',
            'Complete onboarding'
        ],
        'StepType': ['process', 'decision', 'process', 'manual', 'process', 'manual', 'process', 'end'],
        'NextStep': ['S2', '', 'S4', 'S5', 'S6', 'S7', 'S8', ''],
        'YesNext': ['', 'S3', '', '', '', '', '', ''],
        'NoNext': ['', 'S1', '', '', '', '', '', ''],
        'SLA': ['4 hours', '1 day', '2 hours', '1 day', '4 hours', '', '1 week', ''],
        'AutomationPotential': ['Yes', 'No', 'Yes', 'No', 'Yes', 'No', 'No', 'No'],
        'ProcessRisk': ['Low', 'High', 'Medium', 'Low', 'Medium', 'Low', 'Low', 'Low'],
        'ControlDescription': [
            'Automated validation',
            'Manual document check',
            'Auto-provisioning',
            'Physical asset tracking',
            'RBAC enforcement',
            'Manager approval',
            'Calendar integration',
            'Completion checklist'
        ],
        'RelatedDocuments': [
            'HR-Policy-001.pdf',
            'Doc-Verification-Guide.pdf',
            'IT-Provisioning-SOP.pdf',
            'Equipment-Inventory.xlsx',
            'Access-Control-Matrix.xlsx',
            '',
            'Onboarding-Checklist.docx',
            'Onboarding-Completion-Form.pdf'
        ],
        'Notes': [
            'Integrated with background check system',
            'Requires passport and visa check',
            'Auto-creates email and basic access',
            'Laptop, phone, badge assignment',
            'Based on role and department',
            'Manager confirms readiness',
            'First week check-in meeting',
            'Final confirmation and feedback'
        ]
    }
    
    return pd.DataFrame(sample_data)

def display_process_metadata(df_process: pd.DataFrame):
    """Display process metadata and optional field information."""
    st.markdown("### 📊 Process Metadata")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Steps", len(df_process))
    with col2:
        st.metric("Swimlanes", df_process['Lane'].nunique())
    with col3:
        process_id = df_process['ProcessID'].iloc[0] if len(df_process) > 0 else "N/A"
        st.metric("Process ID", process_id)
    with col4:
        # Count automation potential
        if 'AutomationPotential' in df_process.columns:
            auto_count = (df_process['AutomationPotential'].str.lower().isin(['yes', 'y', 'true', '1'])).sum()
            st.metric("Automation Candidates", auto_count)
    
    # Additional metrics for optional fields
    if any(col in df_process.columns for col in ['ProcessRisk', 'SLA', 'RelatedDocuments']):
        st.markdown("#### 📋 Additional Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'ProcessRisk' in df_process.columns:
                high_risk = (df_process['ProcessRisk'].str.lower() == 'high').sum()
                if high_risk > 0:
                    st.warning(f"⚠️ {high_risk} High Risk Step(s)")
                else:
                    st.success("✅ No High Risk Steps")
        
        with col2:
            if 'SLA' in df_process.columns:
                sla_defined = df_process['SLA'].notna().sum()
                st.info(f"⏱️ {sla_defined} Steps with SLA")
        
        with col3:
            if 'RelatedDocuments' in df_process.columns:
                docs_count = df_process['RelatedDocuments'].notna().sum()
                st.info(f"📄 {docs_count} Steps with Documents")

def display_related_documents(df_process: pd.DataFrame):
    """Display related documents as clickable references (if column exists)."""
    if 'RelatedDocuments' not in df_process.columns:
        return
    
    docs_df = df_process[df_process['RelatedDocuments'].notna()][['StepID', 'StepLabel', 'RelatedDocuments']]
    
    if len(docs_df) > 0:
        with st.expander("📎 Related Documents", expanded=False):
            st.markdown("**Documents referenced in this process:**")
            for _, row in docs_df.iterrows():
                st.markdown(f"**{row['StepID']} - {row['StepLabel']}:**")
                docs = str(row['RelatedDocuments']).split(',')
                for doc in docs:
                    doc = doc.strip()
                    if doc:
                        st.markdown(f"  • `{doc}`")

def main():
    """Main application function."""
    
    # Title and description
    st.title("📊 Advanced Process Flow Diagram Generator")
    st.markdown("### Enterprise Process Mapping with Automation & Risk Analysis")
    st.markdown("---")
    
    # Sidebar for configuration and documentation
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Layout orientation option
        st.markdown("### Layout Orientation")
        layout = st.radio(
            "Flow direction",
            ["Horizontal (Left to Right)", "Vertical (Top to Bottom)"],
            index=0,
            key="layout_orientation"
        )
        
        st.markdown("---")
        
        st.markdown("### 📤 Upload Excel File")
        st.markdown("**Required columns:**")
        st.code("""
• ProcessName
• ProcessID
• Lane
• SystemUsed
• StepID
• StepOrder
• StepLabel
• StepType
• NextStep
• YesNext
• NoNext
        """)
        
        st.markdown("**Optional columns:**")
        st.code("""
• Trigger
• FinalOutput
• SLA
• AutomationPotential
• ProcessRisk
• ControlDescription
• RelatedDocuments
• Notes
        """)
        
        st.markdown("---")
        
        st.markdown("### 🎨 Step Types")
        step_type_info = {
            'process': ('Process', '#90EE90', 'Standard step'),
            'decision': ('Decision', '#FFD700', 'Yes/No branch'),
            'manual': ('Manual', '#BA8FD8', 'Human task'),
            'predefined': ('Predefined', '#4682B4', 'Subprocess'),
            'pause': ('Pause', '#FF8C00', 'Wait/delay'),
            'input': ('Input', '#87CEEB', 'Data input'),
            'output': ('Output', '#87CEEB', 'Data output'),
            'form': ('Form', '#D3D3D3', 'Form/doc'),
            'end': ('End', '#FF0000', 'End point')
        }
        
        for step_type, (name, color, desc) in step_type_info.items():
            st.markdown(f"🔹 **{name}**: {desc}")
            st.markdown(f"<div style='background-color:{color}; height:15px; border: 2px solid black; margin: 3px 0;'></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("### 🔍 Visual Indicators")
        st.markdown("""
**Automation Potential = Yes:**
- Dashed border (3px)

**Process Risk = High:**
- Red border (3px)

**SLA Present:**
- ⏱️ Displayed in node

**SystemUsed:**
- [System] in node

**Trigger:**
- ▶ Blue annotation at start

**FinalOutput:**
- ✓ Green annotation at end
        """)
    
    # File upload section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your Process Mapping Excel file",
            type=['xlsx'],
            help="Excel file should contain required columns (any sheet name works)"
        )
    
    with col2:
        if st.button("📋 Use Sample Data", use_container_width=True):
            st.session_state['use_sample'] = True
    
    # Load data
    df = None
    
    if uploaded_file is not None:
        try:
            # Try to read the first sheet automatically
            xl_file = pd.ExcelFile(uploaded_file)
            sheet_names = xl_file.sheet_names
            
            # Try to find common sheet names first, otherwise use first sheet
            common_names = ['Flows', 'Process', 'ProcessMap', 'Sheet1']
            sheet_to_read = None
            
            for name in common_names:
                if name in sheet_names:
                    sheet_to_read = name
                    break
            
            if sheet_to_read is None:
                sheet_to_read = sheet_names[0]
            
            df = pd.read_excel(uploaded_file, sheet_name=sheet_to_read)
            st.success(f"✅ File loaded successfully! Found {len(df)} steps from sheet '{sheet_to_read}'")
            st.session_state['use_sample'] = False
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("💡 Make sure your Excel file contains the required columns")
    
    elif st.session_state.get('use_sample', False):
        df = create_sample_data()
        st.info("📋 Using comprehensive sample data with all features")
    
    # Process the data if available
    if df is not None:
        # Validate columns
        is_valid, validation_msg = validate_columns(df)
        
        if not is_valid:
            st.error(f"❌ {validation_msg}")
            return
        else:
            st.info(validation_msg)
        
        # Get unique processes
        processes = sorted(df['ProcessName'].unique())
        
        if len(processes) == 0:
            st.warning("⚠️ No processes found in the file")
            return
        
        # Process selection
        st.markdown("### 🔍 Select Process")
        selected_process = st.selectbox(
            "Choose a process to visualize",
            processes,
            key="process_selector"
        )
        
        if selected_process:
            # Filter data for selected process
            df_process = df[df['ProcessName'] == selected_process].copy()
            
            # Display process metadata
            display_process_metadata(df_process)
            
            st.markdown("---")
            
            # Generate and display diagram
            st.markdown("### 📊 Process Flow Diagram")
            
            try:
                # Determine orientation based on layout selection
                orientation = 'LR' if 'Horizontal' in st.session_state.get('layout_orientation', 'Horizontal') else 'TB'
                
                with st.spinner("Generating enhanced diagram..."):
                    flow_diagram = build_flow_for_process(df_process, selected_process, orientation)
                
                # Display the diagram
                st.graphviz_chart(flow_diagram, use_container_width=True)
                
                # Download button for DOT source
                dot_source = flow_diagram.source
                st.download_button(
                    label="📥 Download DOT Source",
                    data=dot_source,
                    file_name=f"{selected_process.replace(' ', '_')}_flow.dot",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ Error generating diagram: {str(e)}")
                st.exception(e)
            
            # Display related documents
            display_related_documents(df_process)
            
            # Display filtered data
            st.markdown("---")
            st.markdown("### 📋 Process Steps Details")
            
            # Select columns to display (all available columns)
            display_cols = [col for col in df_process.columns if col in [
                'StepOrder', 'Lane', 'StepID', 'StepLabel', 'StepType', 
                'SystemUsed', 'NextStep', 'YesNext', 'NoNext', 'SLA',
                'AutomationPotential', 'ProcessRisk', 'ControlDescription',
                'RelatedDocuments', 'Notes'
            ]]
            
            display_df = df_process[display_cols].copy()
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_process.to_excel(writer, sheet_name='ProcessDetails', index=False)
            
            st.download_button(
                label="📥 Download Process Details (Excel)",
                data=output.getvalue(),
                file_name=f"{selected_process.replace(' ', '_')}_details.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    else:
        # Welcome screen
        st.info("👆 Please upload an Excel file or use the sample data to get started")
        
        st.markdown("### 📖 How to Use")
        st.markdown("""
        1. **Prepare your Excel file** with required columns (see sidebar)
        2. **Upload the file** using the file uploader above
        3. **Select a process** from the dropdown menu
        4. **View the enhanced diagram** with all annotations
        5. **Download** the diagram source or process details
        
        #### 🎯 Enhanced Features:
        - ✅ **SystemUsed** displayed in each node
        - ✅ **Trigger** shown at process start
        - ✅ **FinalOutput** shown at process end
        - ✅ **SLA** displayed with ⏱️ icon in nodes
        - ✅ **AutomationPotential=Yes**: Dashed border
        - ✅ **ProcessRisk=High**: Red border
        - ✅ **Cross-lane** connections: Dashed lines
        - ✅ **Related Documents**: Clickable references
        - ✅ **Layout Options**: Horizontal or Vertical
        - ✅ **Professional Styling**: Enterprise-ready diagrams
        """)
        
        st.markdown("### 🌟 Try the Sample Data")
        st.markdown("""
        Click **'Use Sample Data'** above to see a complete example with:
        - Employee Onboarding process (8 steps)
        - Multiple swimlanes (HR, IT, Manager)
        - All optional fields populated
        - Automation candidates highlighted
        - Risk indicators
        - SLA annotations
        - Related documents
        """)

if __name__ == "__main__":
    main()
