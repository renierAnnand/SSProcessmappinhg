"""
Process Flow Diagram Generator - SEQUENTIAL VERSION
Guaranteed sequential ordering using lane labels instead of clusters
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

def build_flow_for_process(df_proc: pd.DataFrame, process_name: str, orientation: str = 'LR') -> graphviz.Digraph:
    """Build Graphviz flowchart with guaranteed sequential ordering using lane labels."""
    
    # Create main graph
    dot = graphviz.Digraph(comment=process_name, engine='dot')
    dot.attr(rankdir=orientation, splines='ortho', nodesep='1.0', ranksep='1.8')
    dot.attr('node', fontname='Arial', fontsize='11', margin='0.3')
    dot.attr('edge', fontname='Arial', fontsize='10', color='black', penwidth='1.5')
    
    # Add process title header
    dot.attr(label=process_name, labelloc='t', labeljust='l', fontsize='16', fontname='Arial Bold')
    
    # Sort by StepOrder
    df_sorted = df_proc.sort_values('StepOrder').reset_index(drop=True)
    
    # Add all nodes with lane information in the label
    for _, row in df_sorted.iterrows():
        step_id = str(row['StepID'])
        step_label = str(row['StepLabel'])
        lane = str(row['Lane'])
        step_type = str(row['StepType'])
        
        # Get attributes for this step type
        attrs = get_step_attributes(step_type)
        
        # Add lane to the label with clear separation
        full_label = f"[{lane}]\\n{step_label}"
        
        # Add the node
        dot.node(step_id, full_label, **attrs)
    
    # Create rank groups for sequential ordering
    step_orders = sorted(df_sorted['StepOrder'].unique())
    
    for order in step_orders:
        steps_at_order = df_sorted[df_sorted['StepOrder'] == order]['StepID'].tolist()
        
        # Force all steps at same order to be at same rank
        with dot.subgraph() as s:
            s.attr(rank='same')
            for step_id in steps_at_order:
                s.node(str(step_id))
    
    # Add edges to enforce sequential flow
    for i in range(len(df_sorted) - 1):
        current_step = str(df_sorted.iloc[i]['StepID'])
        next_step = str(df_sorted.iloc[i+1]['StepID'])
        
        # Add invisible edge to maintain order
        dot.edge(current_step, next_step, style='invis', weight='10')
    
    # Add visible edges (connections between steps)
    for _, row in df_sorted.iterrows():
        step_id = str(row['StepID'])
        step_type = str(row['StepType']).lower().strip()
        
        # Handle decision nodes with Yes/No branches
        if step_type == 'decision':
            # Check for YesNext and NoNext first (standard approach)
            yes_next = str(row['YesNext']) if pd.notna(row['YesNext']) else ''
            no_next = str(row['NoNext']) if pd.notna(row['NoNext']) else ''
            next_step = str(row['NextStep']) if pd.notna(row['NextStep']) else ''
            
            # Flexible logic: Handle different data conventions
            # Convention 1: YesNext and NoNext are filled (standard)
            # Convention 2: NextStep (as Yes) and YesNext (as No) are filled
            
            if yes_next and yes_next != 'nan' and yes_next != '':
                # YesNext is populated - use it
                if no_next and no_next != 'nan' and no_next != '':
                    # Both YesNext and NoNext exist (standard convention)
                    dot.edge(step_id, yes_next, label='Yes', color='green', fontcolor='green', 
                            penwidth='2', arrowhead='normal', constraint='false')
                    dot.edge(step_id, no_next, label='No', color='red', fontcolor='red',
                            penwidth='2', arrowhead='normal', constraint='false')
                else:
                    # Only YesNext exists, treat as "No" rejection path (backward loop)
                    # and NextStep as "Yes" approval path (forward)
                    if next_step and next_step != 'nan' and next_step != '':
                        dot.edge(step_id, next_step, label='Yes', color='green', fontcolor='green',
                                penwidth='2', arrowhead='normal', constraint='false')
                    dot.edge(step_id, yes_next, label='No', color='red', fontcolor='red',
                            penwidth='2', arrowhead='normal', constraint='false')
            elif next_step and next_step != 'nan' and next_step != '':
                # Only NextStep exists for decision - unusual but handle it
                dot.edge(step_id, next_step, label='Yes', color='green', fontcolor='green',
                        penwidth='2', arrowhead='normal', constraint='false')
        else:
            # Normal flow using NextStep
            next_step = str(row['NextStep'])
            if pd.notna(row['NextStep']) and next_step != 'nan' and next_step != '':
                dot.edge(step_id, next_step, penwidth='2', arrowhead='normal', constraint='false')
    
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
    st.markdown("### Sequential Process Flow Diagrams (Guaranteed Order)")
    st.markdown("---")
    
    # Sidebar for configuration
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
        step_type_info = {
            'process': ('Process', '#90EE90', 'Standard automated step'),
            'decision': ('Decision', '#FFD700', 'Yes/No branching'),
            'manual': ('Manual', '#BA8FD8', 'Manual task'),
            'predefined': ('Predefined', '#4682B4', 'Subprocess'),
            'pause': ('Pause', '#FF8C00', 'Wait/delay (dashed)'),
            'input': ('Input', '#87CEEB', 'Data input'),
            'output': ('Output', '#87CEEB', 'Data output'),
            'form': ('Form', '#D3D3D3', 'Form/document (dashed)'),
            'end': ('End', '#FF0000', 'Process end')
        }
        
        for step_type, (name, color, desc) in step_type_info.items():
            st.markdown(f"🔹 **{name}**: {desc}")
            st.markdown(f"<div style='background-color:{color}; height:20px; border: 2px solid black; margin: 5px 0;'></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("💡 **Note**: This version uses lane labels instead of swimlane boxes to guarantee perfect sequential ordering from Step 1 to final step.")
    
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
                # Determine orientation based on layout selection
                orientation = 'LR' if 'Horizontal' in st.session_state.get('layout_orientation', 'Horizontal') else 'TB'
                
                with st.spinner("Generating diagram..."):
                    flow_diagram = build_flow_for_process(df_process, selected_process, orientation)
                
                # Render diagram to multiple formats
                diagram_name = selected_process.replace(' ', '_')
                
                # Render to PNG for display and download
                png_data = flow_diagram.pipe(format='png')
                
                # Render to SVG for scalable download
                svg_data = flow_diagram.pipe(format='svg')
                
                # Display the diagram with zoom capability
                st.image(png_data, use_column_width=True, caption="Click image to zoom")
                
                st.info("💡 **Tip**: Click the image above to zoom in/out and view details")
                
                # Download buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        label="📥 Download PNG Image",
                        data=png_data,
                        file_name=f"{diagram_name}_flow.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                with col2:
                    st.download_button(
                        label="📥 Download SVG (Scalable)",
                        data=svg_data,
                        file_name=f"{diagram_name}_flow.svg",
                        mime="image/svg+xml",
                        use_container_width=True
                    )
                
                with col3:
                    # Download button for DOT source
                    dot_source = flow_diagram.source
                    st.download_button(
                        label="📥 Download DOT Source",
                        data=dot_source,
                        file_name=f"{diagram_name}_flow.dot",
                        mime="text/plain",
                        use_container_width=True
                    )
                
            except Exception as e:
                st.error(f"❌ Error generating diagram: {str(e)}")
                st.exception(e)
            
            # Display filtered data
            st.markdown("---")
            st.markdown("### 📋 Process Steps Details")
            
            # Display dataframe with formatting
            display_df = df_process[['StepOrder', 'Lane', 'StepID', 'StepLabel', 'StepType', 'NextStep', 'YesNext', 'NoNext']].copy()
            display_df = display_df.sort_values('StepOrder')
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
        4. **View the generated diagram** with GUARANTEED sequential ordering
        5. **Click the image to zoom** and explore details
        6. **Download** in multiple formats (PNG, SVG, or DOT source)
        
        #### Features:
        - ✅ **GUARANTEED sequential ordering** (Step 1 → Step 2 → ... → Final Step)
        - ✅ **Click-to-zoom** for detailed viewing of large diagrams
        - ✅ **Multiple download formats**: PNG image, SVG (scalable), DOT source
        - ✅ Lane information shown in node labels (e.g., "[Lane Name] Step Description")
        - ✅ Support for 9 different step types with custom shapes and colors
        - ✅ Decision branching with Yes/No paths
        - ✅ Horizontal or vertical flow layout
        - ✅ Professional business process diagram styling
        
        #### Design Trade-off:
        This version prioritizes **perfect sequential ordering** over traditional swimlane boxes.
        Lane information is included within each node label for clarity.
        """)

if __name__ == "__main__":
    main()
