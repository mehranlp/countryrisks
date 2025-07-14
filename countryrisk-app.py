import pandas as pd
import numpy as np
import requests
import plotly.express as px
import dash
from dash import dcc, html

# ------------------------------
# Step 1: Fetch World Bank Data
# ------------------------------

# Define World Bank indicator codes
indicators = {
    'GDP_Growth': 'NY.GDP.MKTP.KD.ZG',           # GDP growth (annual %)
    'Inflation_Rate': 'FP.CPI.TOTL.ZG',          # Inflation, consumer prices (annual %)
    'Unemployment_Rate': 'SL.UEM.TOTL.ZS',       # Unemployment (% of total labor force)
    'FX_Reserves': 'FI.RES.TOTL.CD',             # Total reserves (current US$)
    'Gov_Budget_Balance': 'GC.BAL.CASH.GD.ZS'    # Cash surplus/deficit (% of GDP)
}

# Fetch latest available data (default to 2022)
def fetch_indicator(indicator_code):
    url = f"http://api.worldbank.org/v2/country/all/indicator/{indicator_code}?format=json&date=2022&per_page=500"
    response = requests.get(url)
    data = response.json()[1]
    return {entry['country']['value']: entry['value'] for entry in data if entry['value'] is not None}

# Build dataframe
data_dict = {}

for metric, code in indicators.items():
    data_dict[metric] = fetch_indicator(code)

# Create dataframe with countries as rows
df = pd.DataFrame(data_dict)
df.index.name = 'Country'
df.reset_index(inplace=True)

# ------------------------------
# Step 2: Manual PMI Assignment
# ------------------------------

# Dummy PMI data (replace as needed)
pmi_data = {
    'United States': {'Manufacturing_PMI': 52, 'Services_PMI': 51},
    'China': {'Manufacturing_PMI': 49, 'Services_PMI': 48},
    'Germany': {'Manufacturing_PMI': 47, 'Services_PMI': 49},
    # Add more countries as needed
}

# Default PMI (assume 50 if missing)
def assign_pmi(country):
    pmi = pmi_data.get(country, {'Manufacturing_PMI': 50, 'Services_PMI': 50})
    return pd.Series([pmi['Manufacturing_PMI'], pmi['Services_PMI']])

# Apply PMI values
df[['Manufacturing_PMI', 'Services_PMI']] = df['Country'].apply(assign_pmi)

# ------------------------------
# Step 3: Compute Risk Score
# ------------------------------

def compute_risk(row):
    score = 0
    score += row['GDP_Growth'] * (-0.4)
    score += row['Inflation_Rate'] * 0.4
    score += row['Unemployment_Rate'] * 0.3
    score += row['FX_Reserves'] * (-0.1 / 1e9)  # scale FX reserves
    score += row['Gov_Budget_Balance'] * (-0.2)
    
    score += -0.2 if row['Manufacturing_PMI'] > 50 else 0.3
    score += -0.2 if row['Services_PMI'] > 50 else 0.3
    
    return score


df['Risk_Score'] = df.apply(compute_risk, axis=1)

# ------------------------------
# Step 4: Classify Risk Levels
# ------------------------------

def classify_risk(score):
    if score <= 0:
        return 'Very_Low'
    elif score <= 2:
        return 'Low'
    elif score <= 5:
        return 'Moderate'
    elif score <= 8:
        return 'High'
    else:
        return 'Very_High'

df['Risk_Level'] = df['Risk_Score'].apply(classify_risk)

# ------------------------------
# Step 5: Plotly Dash App
# ------------------------------

color_map = {
    'Very_Low': 'darkgreen',
    'Low': 'green',
    'Moderate': 'yellow',
    'High': 'orange',
    'Very_High': 'red'
}

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1('Global Country Risk Map'),
    dcc.Graph(
        figure=px.choropleth(
            data_frame=df,
            locations='Country',
            locationmode='country names',
            color='Risk_Level',
            hover_name='Country',
            hover_data=['GDP_Growth', 'Inflation_Rate', 'Unemployment_Rate',
                        'FX_Reserves', 'Gov_Budget_Balance',
                        'Manufacturing_PMI', 'Services_PMI', 'Risk_Score'],
            color_discrete_map=color_map,
            title='Country Risk Levels (Based on Weighted Macro Indicators)'
        ).update_geos(visible=False, showcountries=True).update_layout(height=800, width=1400)
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
