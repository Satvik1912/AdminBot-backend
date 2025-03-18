
import google.generativeai as genai
from app.core.config import config
import pandas as pd
import plotly.express as px
import os
import uuid
import logging
from app.core.config import CHARTS_DIR
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
os.makedirs(CHARTS_DIR, exist_ok=True)

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

import logging
import pandas as pd

logger = logging.getLogger(__name__)



def determine_x_y_columns(df, user_query):
    """
    Ensures correct X and Y selection for rankings, trend analysis, and correlations.
    """
    query_lower = user_query.lower()
    numerical_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    
    x_col, y_col = None, None  # Default empty values

    ### ✅ 1. Handle Ranking Queries (Fix for Top Customers Query) ###
    if any(term in query_lower for term in ["top", "highest", "largest", "most"]):
        # **Fix:** Prioritize customer name for X-axis
        if "name" in df.columns:
            x_col = "name"
        elif "customer_name" in df.columns:
            x_col = "customer_name"
        elif "user_id" in df.columns:
            x_col = "user_id"

        # **Ensure Y is always a sum, total, or amount**
        y_col = "total_loan_amount" if "total_loan_amount" in df.columns else "principal" if "principal" in df.columns else None
    if any(term in query_lower for term in ["spread", "variance", "outliers", "distribution"]):
        # **Fix:** Box plots require a numerical Y-axis, X can be None
        y_col = "principal" if "principal" in df.columns else numerical_cols[0] if numerical_cols else None

    elif any(term in query_lower for term in ["distribution", "spread", "range", "frequency"]):
        # **Fix:** Use principal for histogram if available
        if "principal" in df.columns:
            x_col = "principal"
        elif numerical_cols:
            x_col = numerical_cols[0]

        # **Histogram doesn’t need a Y-axis**
        y_col = None  

    ### ✅ 2. Ranking Queries for Loans (Top Loans) ###
    elif any(term in query_lower for term in ["top loans", "largest loans", "biggest loans"]):
        x_col = "loan_id" if "loan_id" in df.columns else None
        y_col = "principal" if "principal" in df.columns else "loan_amount" if "loan_amount" in df.columns else None

    ### ✅ 3. Trend Analysis ###
    elif any(term in query_lower for term in ["trend", "monthly", "yearly", "over time", "history"]):
        if "year" in df.columns and "month" in df.columns:
            df["year_month"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str) + "-01")
            x_col = "year_month"
        else:
            x_col = "disbursed_date" if "disbursed_date" in df.columns else None
        
        y_col = "loan_count" if "loan_count" in df.columns else "COUNT(*)" if "COUNT(*)" in df.columns else "principal"

    if "loan_amount_range" in df.columns:
        x_col = "loan_amount_range"  # **Fix:** Treat as categorical X-axis
        y_col = "loan_count" if "loan_count" in df.columns else None 

    ### ✅ 4. Correlation Queries ###
    elif "correlation" in query_lower or "relationship" in query_lower:
        correlation_terms = ["between", "vs", "and"]
        x_candidate, y_candidate = None, None
        
        for term in correlation_terms:
            if term in query_lower:
                parts = query_lower.split(term)
                if len(parts) == 2:
                    x_candidate, y_candidate = parts[0].strip(), parts[1].strip()

        x_col = next((col for col in numerical_cols if x_candidate and x_candidate in col.lower()), None)
        y_col = next((col for col in numerical_cols if y_candidate and y_candidate in col.lower() and col != x_col), None)

        if not x_col and numerical_cols:
            x_col = numerical_cols[0]
        if (not y_col or x_col == y_col) and len(numerical_cols) > 1:
            y_col = next((col for col in numerical_cols if col != x_col), None)

    ### ✅ 5. General Numerical Data Queries ###
    elif numerical_cols:
        y_col = "principal" if "principal" in df.columns else numerical_cols[0]
        x_col = next((col for col in categorical_cols if col not in [y_col]), None)

    ### ✅ 6. Ensure X and Y Are Distinct ###
    if x_col == y_col:
        y_col = next((col for col in numerical_cols if col != x_col), None)

    ### ✅ 7. Emergency Fallbacks ###
    if not x_col:
        x_col = "loan_id" if "loan_id" in df.columns else None
    if not y_col and numerical_cols:
        y_col = numerical_cols[0]

    if not x_col or not y_col:
        logger.warning(f"Could not determine valid X and Y columns for query: {user_query}")
        return None, None

    logger.info(f"Selected X: {x_col}, Y: {y_col} for query: {user_query}")
    return x_col, y_col


def get_chart_suggestion(data: List[Dict[str, Any]], user_query: str) -> str:
    """
    Determines the best chart type based on the query intent and data structure.

    - Ensures charts are suggested for key insights like trends, comparisons, and distributions.
    - Uses bar charts for rankings, line charts for trends, pie charts for distributions, and more.
    - Includes scatter plots, histograms, heatmaps, and box plots for deeper analysis.
    """
    if not data:
        logger.warning("Empty data provided for chart suggestion")
        return "no_chart"

    df = pd.DataFrame(data)
    numerical_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    query_lower = user_query.lower()

    # ✅ 1. Rankings (e.g., "top loans", "highest disbursed loans")
    if any(term in query_lower for term in ["top", "highest", "largest", "disbursed", "loan amount"]):
        return "bar_horizontal" if len(df) > 10 else "bar"

    # ✅ 2. Trend Analysis (e.g., "monthly loan disbursement trend")
    if any(term in query_lower for term in ["trend", "history", "over time", "monthly", "yearly", "growth"]):
        return "line"

    # ✅ 3. Distribution & Shares (e.g., "loan type distribution")
    if any(term in query_lower for term in ["distribution", "breakdown", "share", "percentage"]):
        return "pie" if len(categorical_cols) > 0 else "bar_stacked"

    # ✅ 4. Correlation & Relationships (e.g., "correlation between tenure and salary")
    if len(numerical_cols) >= 2 and any(term in query_lower for term in ["relationship", "correlation", "vs", "between"]):
        return "scatter"

    # ✅ 5. Loan Amount & Principal Analysis (e.g., "loan amounts over time")
    if any(term in query_lower for term in ["loan amount", "principal", "disbursed amount", "total loan"]):
        return "bar"

    # ✅ 6. Frequency Distribution (e.g., "how many customers have a loan above 50k?")
    if any(term in query_lower for term in ["frequency", "how many", "count", "distribution"]):
        return "histogram"

    # ✅ 7. Outlier & Spread Analysis (e.g., "what is the distribution of loan amounts?")
    if any(term in query_lower for term in ["spread", "variance", "distribution", "outliers"]):
        return "box"

    # ✅ 8. Comparison Between Categories (e.g., "loan approvals by region")
    if len(categorical_cols) >= 2 and any(term in query_lower for term in ["comparison", "matrix", "relationship"]):
        return "heatmap"

    # ✅ 9. Default Fallback - Use Bar Chart if No Other Match
    return "bar"



def generate_plotly_chart(data: List[Dict[str, Any]], chart_type: str, user_query: str) -> str:

    """
    Generates a Plotly chart based on the query and loan data.

    - Ensures charts are always generated for important loan queries.
    - Determines the best chart type dynamically.
    - Saves the chart and returns the file path.
    """
    if not data:
        logger.warning("Empty data provided for chart generation")
        return ""

    try:
        df = pd.DataFrame(data)

        # Determine the best chart type
        chart_type = get_chart_suggestion(data, user_query)
        if chart_type == "no_chart":
            logger.info("No chart recommended for this query")
            return ""

        # Get the best X and Y columns
        x_col, y_col = determine_x_y_columns(df, user_query)
        if not x_col or not y_col:
            logger.warning(f"Could not determine appropriate columns for query: {user_query}")
            return ""

        # Create the chart
        if chart_type == "line":
    # If the x-axis is the combined year_month column, convert it to datetime
            if x_col == "year_month":
                try:
                    df[x_col] = pd.to_datetime(df[x_col] + "-01")
                except Exception as e:
                    logger.error(f"Error converting year_month to datetime: {e}")
            # Now sort and plot the line chart
            if pd.api.types.is_datetime64_dtype(df[x_col]):
                df_sorted = df.sort_values(by=x_col)
                fig = px.line(df_sorted, x=x_col, y=y_col,
                            title=f"{y_col.replace('_', ' ').title()} Trend by {x_col.replace('_', ' ').title()}",
                            labels={x_col: x_col.replace('_', ' ').title(), 
                                    y_col: y_col.replace('_', ' ').title()})
            else:
                grouped_df = df.groupby(x_col)[y_col].mean().reset_index()
                fig = px.line(grouped_df, x=x_col, y=y_col,
                            title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                            labels={x_col: x_col.replace('_', ' ').title(), 
                                    y_col: y_col.replace('_', ' ').title()})
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col.title()} by {x_col.title()}")

        elif chart_type == "bar_horizontal":
            fig = px.bar(df, y=x_col, x=y_col, orientation="h", title=f"{y_col.title()} by {x_col.title()}")

        elif chart_type == "pie":
            fig = px.pie(df, values=y_col, names=x_col, title=f"Distribution of {y_col.title()} by {x_col.title()}")

        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col.title()} vs {x_col.title()}")

        elif chart_type == "bar_stacked":
            fig = px.bar(df, x=x_col, y=y_col, color=x_col, title=f"{y_col.title()} by {x_col.title()} (Stacked)")

        else:
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col.title()} by {x_col.title()}")
            
        # fig.update_layout(yaxis=dict(title="Interest Rate (%)", range=[0, 15]))

        # Save the chart
        chart_filename = f"{uuid.uuid4().hex}.png"
        chart_path = os.path.join(CHARTS_DIR, chart_filename)
        fig.write_image(chart_path)

        logger.info(f"Chart saved as {chart_path}")
        return chart_path

    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return ""
