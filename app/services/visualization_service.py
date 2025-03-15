import google.generativeai as genai
from app.core.config import config
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import uuid
from datetime import datetime
import google.generativeai as genai
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def get_chart_suggestion(data, user_query):
    """Uses Gemini to suggest the best chart type for visualizing the data."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)

        # Identify numerical and categorical columns
        numerical_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
        date_cols = [col for col in df.columns if "date" in col.lower()]

        # Define keyword-based chart selection
        query_lower = user_query.lower()
        if any(word in query_lower for word in ["trend", "growth", "over time", "timeline", "emi payments"]):
            return "line" if date_cols else "bar"
        elif any(word in query_lower for word in ["compare", "highest", "top", "biggest", "ranking"]):
            return "bar"
        elif any(word in query_lower for word in ["distribution", "spread", "cibil", "loan amounts"]):
            return "histogram"
        elif any(word in query_lower for word in ["percentage", "share", "breakdown"]):
            return "pie" if len(categorical_cols) == 1 else "bar"
        elif any(word in query_lower for word in ["relationship", "correlation", "effect"]):
            return "scatter" if len(numerical_cols) >= 2 else "bar"
        elif any(word in query_lower for word in ["comparison", "loan type"]):
            return "bar"
        elif any(word in query_lower for word in ["outliers", "deviation"]):
            return "box"

        # If no clear match, send the data to Gemini for a decision
        column_info = "\n".join([f"{col} ({df[col].dtype})" for col in df.columns])
        prompt = f"""
        You are an expert data visualization consultant. Based on the data structure and user query,
        recommend the BEST chart type for visualization.

        ## USER QUERY
        {user_query}

        ## DATA STRUCTURE
        Number of rows: {len(df)}
        Columns:
        {column_info}

        ## AVAILABLE CHART TYPES
        - bar: For comparing categories
        - line: For trends over time or sequences
        - pie: For part-to-whole relationships (limit to 7 categories max)
        - scatter: For relationships between two numerical variables
        - area: For cumulative totals over time
        - box: For distribution and outliers
        - histogram: For distribution of a single variable
        - heatmap: For showing patterns in a matrix of data

        ## RULES
        - Choose ONLY ONE chart type based on the data and query
        - For time-related queries, prefer line or area charts
        - For category comparisons, prefer bar charts
        - Limit pie charts to 7 categories or fewer
        - Recommend box or histogram for distribution analysis

        ## OUTPUT FORMAT
        Return ONLY ONE of the chart types listed above as a single word, with no explanation or additional text.
        """

        response = model.generate_content(prompt)
        chart_type = response.text.strip().lower()

        # Validate chart type
        valid_types = ["bar", "line", "pie", "scatter", "area", "box", "histogram", "heatmap"]
        if chart_type not in valid_types:
            logger.warning(f"Invalid chart type suggested: {chart_type}, defaulting to bar")
            return "bar"

        logger.info(f"Suggested chart type: {chart_type}")
        return chart_type

    except Exception as e:
        logger.error(f"Error getting chart suggestion: {str(e)}")
        return "bar"  # Default to bar chart on error
    
# ======================== PLOTLY CHART GENERATION ========================
def generate_plotly_chart(data, chart_type, user_query):
    """Generates a Plotly chart based on the data and suggested chart type."""
    if not data:
        logger.warning("No data provided for chart generation")
        return None

    # Create a timestamp for unique chart naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    chart_path = f"chart_{unique_id}{chart_type}{timestamp}.png"

    try:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data)

        # Ensure loan_amount is always used for the Y-axis
        if "loan_amount" not in df.columns:
            logger.error("No loan_amount column found. Using fallback column.")
            y_col = df.select_dtypes(include=['number']).columns[0]  # Fallback to first numeric column
        else:
            y_col = "loan_amount"

        # Determine X-axis column intelligently
        if "customer_name" in df.columns and any(keyword in user_query.lower() for keyword in ["top", "highest", "biggest"]):
            x_col = "customer_name"  # Use customer name for top loan queries
        elif "loan_date" in df.columns and "trend" in user_query.lower():
            x_col = "loan_date"  # Use date for time-based queries
        elif "loan_type" in df.columns and "loan amount" not in user_query.lower():
            x_col = "loan_type"  # Default category when not asking for specific amounts
        else:
            x_col = df.columns[0]  # Fallback to the first column

        # Create chart title based on user query
        chart_title = f"Loan Data: {user_query}"
        if len(chart_title) > 70:
            chart_title = chart_title[:67] + "..."

        # Generate appropriate chart based on type
        fig = None

        if chart_type == "bar":
            df = df.sort_values(by=y_col, ascending=False)
            fig = px.bar(df, x=x_col, y=y_col, title=chart_title, color=x_col, text=y_col)

        elif chart_type == "line":
            if "loan_date" in df.columns:
                df["loan_date"] = pd.to_datetime(df["loan_date"])
                df = df.sort_values(by="loan_date")
                fig = px.line(df, x="loan_date", y=y_col, title=chart_title, markers=True)

        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=chart_title)

        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)

        elif chart_type == "area":
            if "loan_date" in df.columns:
                df["loan_date"] = pd.to_datetime(df["loan_date"])
                df = df.sort_values(by="loan_date")
                fig = px.area(df, x="loan_date", y=y_col, title=chart_title)

        elif chart_type == "histogram":
            fig = px.histogram(df, x=y_col, title=chart_title)

        elif chart_type == "box":
            fig = px.box(df, y=y_col, title=chart_title)

        elif chart_type == "heatmap":
            fig = px.imshow(df.corr(), title="Correlation Heatmap")

        # Default to bar chart if no figure was created
        if fig is None:
            logger.warning(f"Could not create {chart_type} chart, defaulting to bar")
            fig = px.bar(df, x=x_col, y=y_col, title=chart_title)

        # Set consistent figure sizing and layout
        fig.update_layout(
            width=1000,
            height=600,
            template="plotly_white",
            title={'text': chart_title, 'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}
        )

        # Save the figure as an image
        fig.write_image(chart_path)
        logger.info(f"Chart generated at {chart_path}")
        return chart_path

    except Exception as e:
        logger.error(f"Error generating Plotly chart: {str(e)}")
        return None