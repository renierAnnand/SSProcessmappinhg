"""
Process Flow Diagram Generator
Automated swimlane process flow diagrams from Excel templates
"""

import streamlit as st
import pandas as pd
import graphviz
from typing import Dict, Tuple
import io

# Page configuration
st.set_page_config(
    page_title="Process Flow Diagram Generator",
    page_icon="📊",
    layout="wide"
)

# Step type configurations matching flowchart standards
STEP_CONFIGS = {
    'process': {'shape': 'box', 'style': 'filled', 'fillcolor': 'lightgreen', 'color': 'black'},
    'decision': {'shape': 'diamond', 'style': 'filled', 'fillcolor': 'gold', 'color': 'black'},
    'manual': {'shape': 'box', 'style': 'filled', 'fillcolor': 'plum', 'color': 'black'},
    'predefined': {'shape': 'box3d', 'style': 'filled', 'fillcolor': 'lightblue', 'color': 'black'},
    'pause': {'shape': 'hexagon', 'style': 'filled', 'fillcolor': 'orange', 'color': 'black'},
    'input': {'shape': 'parallelogram', 'style': 'filled', 'fillcolor': 'lightblue', 'color': 'black'},
    'output': {'shape': 'parallelogram', 'style': 'filled', 'fillcolor': 'lightblue', 'color': 'black'},
    'form': {'shape': 'note', 'style': 'filled', 'fillcolor': 'lightgrey', 'color': 'black'},
    'end': {'shape': 'oval', 'style': 'filled', 'fillcolor': 'red', 'color': 'black', 'fontcolor': 'white'}
}

def validate_columns(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate that DataFrame contains all required columns."""
    required_columns = [
        'ProcessName', 'ProcessID', 'Lane', 'StepID', 
        'StepOrder', 'StepLabel', 'StepType', 'NextStep', 
        'YesNext', 'NoNext', 'Notes'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    return True, ""

def get_step_attributes(step_type: str) -> Dict[str, str]:
    """Get visual attributes for a given step type."""
    step_type_lower = step_type.lower().strip()
    return STEP_CONFIGS.get(step_type_lower, STEP_CONFIGS['process'])

def build_flow_for_process(df_proc: pd.DataFrame, process_name: str) -> graphviz.Digraph:
    """Build Graphviz flowchart with swimlanes for a given process."""
    # Create main graph with horizontal layout
    dot = graphviz.Digraph(comment=process_name)
    dot.attr(rankdir='LR', splines='ortho', nodesep='0.8', ranksep='1.2')
    dot.attr('node', fontname='Arial', fontsize='10')
    dot.attr('edge', fontname='Arial', fontsize='9')
    
    # Sort by StepOrder
    df_sorted = df_proc.sort_values('StepOrder').reset_index(drop=True)
    
    # Group steps by lane
    lanes = df_sorted['Lane'].unique()
    lane_steps = {lane: df_sorted[df_sorted['Lane'] == lane] for lane in lanes}
    
    # Create swimlanes as subgraphs
    for idx, lane in enumerate(lanes):
        with dot.subgraph(name=f'cluster_{idx}') as cluster:
            cluster.attr(label=str(lane), style='filled', color='lightgrey', fillcolor='#f0f0f0')
            cluster.attr(fontsize='12', fontname='Arial Bold')
            
            # Add nodes for this lane
            lane_df = lane_steps[lane]
            for _, row in lane_df.iterrows():
                step_id = str(row['StepID'])
                step_label = str(row['StepLabel'])
                step_type = str(row['StepType'])
                
                # Get attributes for this step type
                attrs = get_step_attributes(step_type)
                
                # Add the node
                cluster.node(step_id, step_label, **attrs)
    
    # Add edges (connections between steps)
    for _, row in df_sorted.iterrows():
        step_id = str(row['StepID'])
        step_type = str(row['StepType']).lower().strip()
        
        # Handle decision nodes with Yes/No branches
        if step_type == 'decision':
            yes_next = str(row['YesNext'])
            no_next = str(row['NoNext'])
            
            if pd.notna(row['YesNext']) and yes_next != 'nan' and yes_next != '':
                dot.edge(step_id, yes_next, label='Yes', color='green', fontcolor='green')
            
            if pd.notna(row['NoNext']) and no_next != 'nan' and no_next != '':
                dot.edge(step_id, no_next, label='No', color='red', fontcolor='red')
        else:
            # Normal flow using NextStep
            next_step = str(row['NextStep'])
            if pd.notna(row['NextStep']) and next_step != 'nan' and next_step != '':
                dot.edge(step_id, next_step)
    
    return dot

def create_sample_data() -> pd.DataFrame:
    """Create sample data for demonstration."""
    sample_data = {
        'ProcessName': ['Order Processing'] * 10,
        'ProcessID': ['PROC001'] * 10,
        'Lane': ['Customer', 'Sales', 'Sales', 'Warehouse', 'Warehouse', 'Finance', 'Finance', 'Sales', 'Warehouse', 'Customer'],
        'StepID': ['S001', 'S002', 'S003', 'S004', 'S005', 'S006', 'S007', 'S008', 'S009', 'S010'],
        'StepOrder': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'StepLabel': [
            'Submit Order',
            'Review Order',
            'Check Stock',
            'Pick Items',
            'Pack Order',
            'Process Payment',
            'Verify Payment',
            'Send Confirmation',
            'Ship Order',
            'Receive Order'
        ],
        'StepType': ['input', 'manual', 'decision', 'process', 'process', 'process', 'decision', 'output', 'process', 'end'],
        'NextStep': ['S002', 'S003', '', 'S005', 'S006', 'S007', '', 'S009', 'S010', ''],
        'YesNext': ['', '', 'S004', '', '', '', 'S008', '', '', ''],
        'NoNext': ['', '', 'S008', '', '', '', 'S003', '', '', ''],
        'Notes': ['Customer places order', 'Sales team reviews', 'Check inventory', 'Warehouse picks items', 
                  'Pack for shipping', 'Process customer payment', 'Verify payment success', 'Email confirmation',
                  'Ship to customer', 'Order complete']
    }
    
    return pd.DataFrame(sample_data)

def main():
    """Main application function."""
    
    # Title and description
    st.title("📊 Process Flow Diagram Generator")
    st.markdown("### Automated Swimlane Process Flow Diagrams from Excel")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.markdown("### Upload Excel File")
        st.markdown("Your Excel file should contain these columns:")
        st.code("""
• ProcessName
• ProcessID
• Lane
• StepID
• StepOrder
• StepLabel
• StepType
• NextStep
• YesNext
• NoNext
• Notes
        """)
        
        st.markdown("### Supported Step Types")
        for step_type, config in STEP_CONFIGS.items():
            color = config['fillcolor']
            st.markdown(f"• **{step_type.title()}**: {config['shape']} ({color})")
    
    # File upload section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your Process Flow Excel file",
            type=['xlsx'],
            help="Excel file should contain the required columns (any sheet name works)"
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
            
            # Try to find 'Flows' sheet first, otherwise use first sheet
            if 'Flows' in sheet_names:
                sheet_to_read = 'Flows'
            else:
                sheet_to_read = sheet_names[0]
                st.info(f"ℹ️ Using sheet: '{sheet_to_read}' (no 'Flows' sheet found)")
            
            df = pd.read_excel(uploaded_file, sheet_name=sheet_to_read)
            st.success(f"✅ File loaded successfully! Found {len(df)} steps from sheet '{sheet_to_read}'")
            st.session_state['use_sample'] = False
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("💡 Make sure your Excel file contains the required columns")
    
    elif st.session_state.get('use_sample', False):
        df = create_sample_data()
        st.info("📋 Using sample data for demonstration")
    
    # Process the data if available
    if df is not None:
        # Validate columns
        is_valid, error_msg = validate_columns(df)
        
        if not is_valid:
            st.error(f"❌ Invalid file structure: {error_msg}")
            return
        
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
            
            # Display process info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Steps", len(df_process))
            with col2:
                st.metric("Swimlanes", df_process['Lane'].nunique())
            with col3:
                process_id = df_process['ProcessID'].iloc[0] if len(df_process) > 0 else "N/A"
                st.metric("Process ID", process_id)
            
            st.markdown("---")
            
            # Generate and display diagram
            st.markdown("### 📊 Process Flow Diagram")
            
            try:
                with st.spinner("Generating diagram..."):
                    flow_diagram = build_flow_for_process(df_process, selected_process)
                
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
            
            # Display filtered data
            st.markdown("---")
            st.markdown("### 📋 Process Steps Details")
            
            # Display dataframe with formatting
            display_df = df_process[['StepOrder', 'Lane', 'StepID', 'StepLabel', 'StepType', 'NextStep', 'YesNext', 'NoNext']].copy()
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
        1. **Prepare your Excel file** with the required columns (any sheet name works)
        2. **Upload the file** using the file uploader above
        3. **Select a process** from the dropdown menu
        4. **View the generated swimlane diagram** and process details
        5. **Download** the diagram source or process details as needed
        
        #### Features:
        - ✅ Automatic swimlane generation based on Lane column
        - ✅ Support for 9 different step types with custom shapes and colors
        - ✅ Decision branching with Yes/No paths
        - ✅ Horizontal left-to-right flow layout
        - ✅ Professional business process diagram styling
        - ✅ Export capabilities for further customization
        - ✅ Works with any sheet name (automatically uses first sheet)
        """)

if __name__ == "__main__":
    main()
