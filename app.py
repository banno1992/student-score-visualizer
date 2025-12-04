import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import zipfile
import textwrap
from matplotlib.backends.backend_pdf import PdfPages

# Set page configuration
st.set_page_config(
    page_title="Student Test Scores Bar Chart Generator",
    page_icon="📊",
    layout="wide"
)

# Title and introduction
st.title("Student Test Scores Visualization")
st.markdown("""
This application generates individual bar charts for student test scores.
Upload a spreadsheet file (Excel or CSV) to create visual representations of each student's performance.
""")

# Sidebar for display options
st.sidebar.header("Display Options")
st.sidebar.subheader("Chart Options")
show_average_line = st.sidebar.checkbox("Show Average Line", value=True)
show_average_bar = st.sidebar.checkbox("Show Average as Bar", value=False)
average_line_color = "#004080"  # Dark blue color for the average line

st.sidebar.subheader("Chart Title")
custom_title_prefix = st.sidebar.text_input("Title prefix (before student name):", value="Test Scores for")
st.sidebar.caption("Example: 'Year 9 Results -' will create 'Year 9 Results - John Smith'")

st.sidebar.subheader("Summary Options")
show_summary_table = st.sidebar.checkbox("Show Summary Table", value=True)
show_individual_summary = st.sidebar.checkbox("Show Individual Student Summary", value=True)

# File upload section
st.header("Upload Data")
uploaded_file = st.file_uploader(
    "Upload your spreadsheet file (Excel or CSV)", 
    type=["xlsx", "xls", "csv"]
)

# Function to validate the data format
def validate_data(df):
    errors = []
    
    # Check if the DataFrame is empty
    if df.empty:
        errors.append("The uploaded file contains no data.")
        return errors, None
    
    # Check if there are at least 3 columns (for student name, subject, and percentage)
    if df.shape[1] < 3:
        errors.append("The file should have at least 3 columns: student name, subject, and percentage.")
        return errors, None
    
    # Assume the first column is student names
    student_col = df.columns[0]
    
    # Identify potential subject and percentage columns
    # For the format: Subject, Percentage, Subject, Percentage...
    potential_pairs = []
    
    for i in range(1, len(df.columns), 2):
        if i+1 < len(df.columns):
            subject_col = df.columns[i]
            percentage_col = df.columns[i+1]
            
            # Check if percentage column name contains "percentage" or "percent" or "%"
            pct_terms = ["percentage", "percent", "%"]
            is_percentage_col = any(term in percentage_col.lower() for term in pct_terms)
            
            potential_pairs.append((subject_col, percentage_col, is_percentage_col))
    
    # If we found valid pairs, use them
    if potential_pairs:
        return errors, {
            "format": "paired",
            "student_col": student_col,
            "subject_percentage_pairs": potential_pairs
        }
    
    # If no structure could be determined, prompt the user to select columns
    return ["Could not automatically determine the data structure. Please select the appropriate columns below."], None

# Function to process data and create charts
def process_data_and_create_charts(df, data_format):
    charts = []
    student_summaries = {}
    
    if data_format["format"] == "paired":
        # Paired format processing (Subject, Percentage, Subject, Percentage...)
        student_col = data_format["student_col"]
        subject_percentage_pairs = data_format["subject_percentage_pairs"]
        
        # Process each student row
        for _, row in df.iterrows():
            student_name = row[student_col]
            subjects = []
            scores = []
            
            # Extract subject and percentage data
            for subject_col, percentage_col, _ in subject_percentage_pairs:
                # Only use pairs where we have valid data
                if pd.notna(row[subject_col]) and pd.notna(row[percentage_col]):
                    subjects.append(subject_col)
                    scores.append(float(row[percentage_col]))
            
            # Skip if no valid data for this student
            if not subjects:
                continue
            
            # Calculate average and total percentage
            avg_score = sum(scores) / len(scores) if scores else 0
            total_possible = 100 * len(scores)
            total_achieved = sum(scores)
            total_percentage = (total_achieved / total_possible) * 100 if total_possible > 0 else 0
            
            # Store summary for this student
            student_summaries[student_name] = {
                "average": avg_score,
                "total_achieved": total_achieved,
                "total_possible": total_possible,
                "total_percentage": total_percentage,
                "num_subjects": len(subjects)
            }
                
            # Create a bar chart for this student
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # If we're showing average as a bar, add it to the subjects and scores
            display_subjects = subjects.copy()
            display_scores = scores.copy()
            
            if show_average_bar:
                display_subjects.append("Average")
                display_scores.append(avg_score)
            
            # Wrap text for long subject names
            wrapped_subjects = []
            for subject in display_subjects:
                # Wrap text to max 15 characters per line
                wrapped = '\n'.join(textwrap.wrap(subject, width=15))
                wrapped_subjects.append(wrapped)
            
            # Use a color palette with a gradient for subject bars
            bars = ax.bar(wrapped_subjects, display_scores, color=['#7792E3'] * len(subjects) + ['#004080'] * (1 if show_average_bar else 0), alpha=0.8)
            
            # Add data labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2., 
                    height,
                    f'{height:.1f}%',
                    ha='center', 
                    va='bottom',
                    fontweight='bold',
                    fontsize=10
                )
            
            # Set axes and title (remove x-axis label)
            ax.set_ylabel('Percentage', fontsize=12)
            chart_title = f'{custom_title_prefix} {student_name}' if custom_title_prefix else student_name
            ax.set_title(chart_title, fontsize=14, fontweight='bold', pad=20)
            
            # Customize x-axis tick labels with rotation to prevent overlapping
            ax.tick_params(axis='x', labelsize=9)
            plt.setp(ax.get_xticklabels(), rotation=60, horizontalalignment='right', rotation_mode="anchor")
            
            # Add average line if enabled
            if show_average_line:
                ax.axhline(y=avg_score, color=average_line_color, linestyle='--', alpha=0.7)
                ax.text(
                    len(subjects) - 0.5, 
                    avg_score + 2, 
                    f'Average: {avg_score:.1f}%', 
                    color=average_line_color,
                    fontweight='bold',
                    ha='right'
                )
            
            # Set y-axis limits to always be 0-105% for fair comparison with padding at top
            ax.set_ylim(bottom=0, top=105)
            
            # Add a grid for better readability
            ax.grid(axis='y', linestyle='--', alpha=0.7)
                
            # Fit image size to accommodate long rotated labels
            plt.tight_layout()
            
            # Save figure to buffer for downloads before closing
            fig_buffer = io.BytesIO()
            fig.savefig(fig_buffer, format='png', bbox_inches='tight')
            fig_buffer.seek(0)
            
            charts.append({
                "student": student_name, 
                "figure": fig, 
                "summary": student_summaries[student_name],
                "figure_buffer": fig_buffer
            })
    
    return charts, student_summaries

# Function to create a download link for the charts
def get_chart_download_link(charts, filename="student_charts.pdf"):
    # Create a buffer to store the PDF
    buffer = io.BytesIO()
    
    # Use PdfPages to create a multi-page PDF
    with PdfPages(buffer) as pdf:
        for chart_info in charts:
            # Extract the figure from chart_info dictionary
            fig = chart_info.get("figure")
            if fig:
                pdf.savefig(fig)
    
    # Set the position to the beginning of the buffer
    buffer.seek(0)
    
    # Generate the download link
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Download All Charts as PDF</a>'
    return href

# Function to get a download link for a single figure
def get_single_chart_download_link(fig, student_name, format="png"):
    buf = io.BytesIO()
    fig.savefig(buf, format=format, bbox_inches='tight')
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode()
    
    if format == "png":
        mime = "image/png"
    elif format == "pdf":
        mime = "application/pdf"
    else:
        mime = "application/octet-stream"
        
    filename = f"{student_name.replace(' ', '_')}_chart.{format}"
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}">Download as {format.upper()}</a>'
    return href

# Function to create a download link for all charts as PNG in a ZIP file
def get_charts_zip_download_link(charts, filename="student_charts.zip"):
    # Create a buffer to store the ZIP file
    buffer = io.BytesIO()
    
    # Create a ZIP file in memory
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for chart in charts:
            student_name = chart["student"]
            
            # Use the saved figure buffer if available
            if "figure_buffer" in chart:
                chart["figure_buffer"].seek(0)
                zip_file.writestr(f"{student_name.replace(' ', '_')}_chart.png", chart["figure_buffer"].getvalue())
            else:
                # Fallback to generating from figure (if not closed yet)
                fig = chart["figure"]
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', bbox_inches='tight')
                img_buf.seek(0)
                zip_file.writestr(f"{student_name.replace(' ', '_')}_chart.png", img_buf.getvalue())
    
    # Reset buffer position
    buffer.seek(0)
    
    # Generate the download link
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="{filename}">Download All Charts as PNG (ZIP)</a>'
    return href

# Main application logic
if uploaded_file is not None:
    try:
        # Try to read the uploaded file
        if uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:  # CSV
            df = pd.read_csv(uploaded_file)
        
        # Display the raw data
        st.header("Raw Data Preview")
        st.dataframe(df.head(10))
        
        # Validate the data format
        errors, data_format = validate_data(df)
        
        if errors:
            st.error("The following issues were found with your data:")
            for error in errors:
                st.warning(error)
                
            # If data format could not be determined, let the user select columns
            if data_format is None:
                st.header("Column Selection")
                st.info("Please select the appropriate columns from your data:")
                
                # Manual selection of columns for paired format
                st.info("Please select the columns for subjects and their corresponding percentages")
                
                student_col = st.selectbox("Select the column containing student names:", df.columns)
                
                # Let user select pairs of subject/percentage columns
                subject_percentage_pairs = []
                
                # Get all potential columns (excluding student column)
                potential_columns = [col for col in df.columns if col != student_col]
                
                # Display selection for up to 5 subject-percentage pairs
                for i in range(0, min(len(potential_columns), 10), 2):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if i < len(potential_columns):
                            subject_col_name = f"subject_col_{i//2 + 1}"
                            subject_col = st.selectbox(f"Subject column #{i//2 + 1}:", 
                                                    potential_columns,
                                                    index=min(i, len(potential_columns)-1),
                                                    key=subject_col_name)
                    
                            # Only process if we have both columns
                            if i+1 < len(potential_columns):
                                with col2:
                                    percentage_col_name = f"percentage_col_{i//2 + 1}"
                                    percentage_col = st.selectbox(f"Percentage column #{i//2 + 1}:", 
                                                            [col for col in potential_columns if col != subject_col],
                                                            index=min(i+1, len(potential_columns)-1),
                                                            key=percentage_col_name)
                                    
                                    # Add this pair to our list
                                    subject_percentage_pairs.append((subject_col, percentage_col, True))
                
                if student_col and subject_percentage_pairs:
                    data_format = {
                        "format": "paired",
                        "student_col": student_col,
                        "subject_percentage_pairs": subject_percentage_pairs
                    }
        
        # If we have a valid data format, process the data and create charts
        if data_format:
            st.header("Generating Charts")
            
            with st.spinner("Processing data and creating charts..."):
                charts, student_summaries = process_data_and_create_charts(df, data_format)
            
            if charts:
                st.success(f"Successfully generated {len(charts)} charts!")
                
                # Create download links for all charts
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(get_chart_download_link(charts), unsafe_allow_html=True)
                with col2:
                    st.markdown(get_charts_zip_download_link(charts), unsafe_allow_html=True)
                
                # Display overall summary table if enabled
                if show_summary_table:
                    st.header("Overall Summary")
                    
                    # Create a DataFrame for the summary
                    summary_data = []
                    for student_name, summary in student_summaries.items():
                        summary_data.append({
                            "Student": student_name,
                            "Average Score (%)": f"{summary['average']:.1f}",
                            "Total Score": f"{summary['total_achieved']:.1f}",
                            "Number of Subjects": summary['num_subjects'],
                            "Overall Percentage": f"{summary['total_percentage']:.1f}%"
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, use_container_width=True)
                
                # Display each chart with individual download options
                st.header("Individual Student Charts")
                
                for chart in charts:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        student_name = chart['student']
                        summary = chart['summary']
                        
                        st.subheader(f"Chart for {student_name}")
                        st.pyplot(chart["figure"])
                        
                        # Close figure after displaying to prevent memory issues
                        plt.close(chart["figure"])
                        
                        # Display individual student summary if enabled
                        if show_individual_summary:
                            st.markdown(f"""
                            **Summary for {student_name}:**
                            - Average Score: **{summary['average']:.1f}%**
                            - Total Score: **{summary['total_achieved']:.1f} out of {summary['total_possible']:.1f}**
                            - Overall Percentage: **{summary['total_percentage']:.1f}%**
                            """)
                    
                    with col2:
                        st.markdown("<br><br><br>", unsafe_allow_html=True)
                        # Use the saved buffer for downloads since figure is closed
                        if "figure_buffer" in chart:
                            chart["figure_buffer"].seek(0)
                            b64 = base64.b64encode(chart["figure_buffer"].getvalue()).decode()
                            png_href = f'<a href="data:image/png;base64,{b64}" download="{chart["student"].replace(" ", "_")}_chart.png">Download as PNG</a>'
                            st.markdown(png_href, unsafe_allow_html=True)
                        else:
                            st.markdown(get_single_chart_download_link(chart["figure"], chart["student"], "png"), unsafe_allow_html=True)
                            st.markdown(get_single_chart_download_link(chart["figure"], chart["student"], "pdf"), unsafe_allow_html=True)
            else:
                st.error("No charts could be generated from the data. Please check your data format.")
    
    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")
        st.info("Please make sure your file is a valid Excel or CSV file with the appropriate data structure.")

else:
    # Display instructions if no file is uploaded
    st.info("""
    ### How to use this application:
    
    1. Prepare your spreadsheet file with student test scores. The file should have:
       - First column with student names
       - Alternating columns with subject names and percentages
       
    2. Upload your Excel (.xlsx, .xls) or CSV file using the uploader above.
    
    3. The application will automatically detect the structure of your data.
       If it cannot, you will be prompted to select the appropriate columns.
       
    4. Review the generated charts for each student.
    
    5. Download individual charts or all charts as a PDF.
    
    ### Example data format:
    
    | Student     | Chemistry | Percentage | Biology | Percentage |
    |-------------|-----------|------------|---------|------------|
    | John Smith  | 8         | 80         | 9       | 100        |
    | Jane Cole   | 7         | 70         | 8       | 89         |
    """)

# Add a footer with some information
st.markdown("---")
st.markdown("### About")
st.markdown("""
This application helps teachers and parents visualize student performance across different subjects.
Upload your spreadsheet data to generate individual bar charts for each student, providing a clear visual 
representation of their test scores and percentages.
""")
