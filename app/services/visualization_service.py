import google.generativeai as genai
from app.core.config import config
import pandas as pd
from fastapi import HTTPException
import pandas as pd
import google.generativeai as genai
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.pyplot as plt

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def get_chart_recommendation(user_input: str) -> str:
    """Uses Gemini API to determine the best chart type for the given query result."""

    prompt = f"""
    Based on the following SQL query: "{user_input}",
    decide the most appropriate chart type from: ["bar", "line", "pie", "scatter", "histogram"].
    Return ONLY one word as the response (e.g., "bar", "line", "pie", "scatter", "histogram").
    Do NOT include explanations, examples, or anything else.
    """

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        chart_type = response.text.strip().lower()

        if chart_type not in ["bar", "line", "pie", "scatter", "histogram"]:
            return "bar"  # Fallback in case of unexpected response

        return chart_type
    except Exception as e:
        print(f"Error determining chart type: {e}")
        return "bar"  # Default fallback

def generate_chart(query_results: list, chart_type: str) -> str:
    """
    Generates a chart based on the recommended type and query results.
    Saves as a PNG image and returns the base64-encoded image.
    """
    try:
        # Convert query results to DataFrame
        df = pd.DataFrame(query_results)

        if len(df.columns) < 2:
            raise HTTPException(status_code=400, detail="Query results must have at least two columns")

        plt.figure(figsize=(8, 5))

        x_column = df.columns[0]  # Assume first column as x-axis
        y_column = df.columns[1]  # Assume second column as y-axis

        if chart_type == "bar":
            sns.barplot(x=df[x_column], y=df[y_column])
        elif chart_type == "line":
            sns.lineplot(data=df, x=x_column, y=y_column, marker='o')
        elif chart_type == "pie":
            plt.pie(df[y_column], labels=df[x_column], autopct='%1.1f%%')
        elif chart_type == "scatter":
            plt.scatter(df[x_column], df[y_column])
        elif chart_type == "histogram":
            plt.hist(df[y_column], bins=10)

        plt.xlabel(x_column)
        plt.ylabel(y_column)
        plt.title(f"{chart_type.capitalize()} Chart")

        # Save to a file
        img_path = f"chart_{chart_type}.png"
        plt.savefig(img_path, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    except Exception as e:
        print(f"Error generating chart {e}")
    