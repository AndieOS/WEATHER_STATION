import pytz
from flask import Flask
import dash
import dash_core_components as dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import mysql.connector
from datetime import datetime, timedelta

# Zona horaria de Ecuador
ecuador_tz = pytz.timezone('Etc/GMT-5')    
now_ecuador = datetime.now(ecuador_tz)

# Configuración de la base de datos
db_config = {
    'host': 'monorail.proxy.rlwy.net',
    'port': '18774',
    'user': 'root',
    'password': 'KUmWNRFpmbrQCUOxgDHOiGNswZaPDELN',
    'database': 'railway'
}

def get_data(start_date=None, end_date=None):
    # Conectar a la base de datos
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Consultar los datos en el rango de fechas
    query = """
        SELECT * FROM emetereologicas
        WHERE (%s IS NULL OR fecha >= %s) AND (%s IS NULL OR fecha <= %s)
    """
    cursor.execute(query, (start_date, start_date, end_date, end_date))
    rows = cursor.fetchall()

    # Organizar los datos por variable
    data = {key: [] for key in ['temperaturaaire', 'humedadaire', 'intensidadluz', 'indiceuv',
                                'velocidadviento', 'direccionviento', 'cantidadlluvia', 
                                'presionbarometrica']}
    timestamps = []
    
    for row in rows:
        timestamps.append(row.get('fecha', ''))
        for key in data.keys():
            data[key].append(row.get(key, 0))  # Append value or 0 if not present

    conn.close()
    return data, timestamps

# Inicializar la aplicación Flask
server = Flask(__name__)

# Crear la aplicación Dash
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "NOVA" 
# Diseño de la aplicación Dash
app.layout = html.Div([
    html.Div(
        children=[
            html.Img(src='/assets/Nova.png', style={'height': '50px', 'margin-right': '10px'}),
            html.Span('Estación Meteorológica', style={'fontSize': '24px', 'fontWeight': 'bold'})
        ],
        style={'backgroundColor': 'green', 'color': 'white', 'display': 'flex', 'alignItems': 'center', 'padding': '10px', 'justifyContent': 'center'}
    ),
    dcc.Tabs([
        dcc.Tab(
            label='Supervisión',
            children=[
                html.Div([
                    html.H1('Variables de Estación Meteorológica', style={'textAlign': 'center'}),
                    html.Div(id='gauge-graphs')
                ])
            ],
            style={'fontWeight': 'bold', 'fontSize': '20px'},
            selected_style={'fontWeight': 'bold', 'fontSize': '20px'}
        ),
        dcc.Tab(
            label='Histórico',
            children=[
                html.Div([
                    html.H2('Seleccionar Variables y Rango de Fechas', style={'textAlign': 'center'}),
                    html.Div([
                        html.Label('Seleccionar Variables:'),
                        dcc.Checklist(
                            id='variable-selector',
                            options=[
                                {'label': 'Temperatura Aire', 'value': 'temperaturaaire'},
                                {'label': 'Humedad Aire', 'value': 'humedadaire'},
                                {'label': 'Intensidad Luz', 'value': 'intensidadluz'},
                                {'label': 'Índice UV', 'value': 'indiceuv'},
                                {'label': 'Velocidad Viento', 'value': 'velocidadviento'},
                                {'label': 'Dirección Viento', 'value': 'direccionviento'},
                                {'label': 'Cantidad Lluvia', 'value': 'cantidadlluvia'},
                                {'label': 'Presión Barométrica', 'value': 'presionbarometrica'}
                            ],
                            value=['temperaturaaire']
                        )
                    ]),
                    html.Div([
                        html.Label('Seleccionar Rango de Fechas:'),
                        dcc.DatePickerRange(
                            id='date-picker-range',
                            start_date=now_ecuador - timedelta(days=1),
                            end_date=now_ecuador,
                            display_format='DD/MM/YYYY'
                        )
                    ]),
                    dcc.Graph(id='custom-graph')
                ])
            ],
            style={'fontWeight': 'bold', 'fontSize': '20px'},
            selected_style={'fontWeight': 'bold', 'fontSize': '20px'}
        )
    ])
])
@app.callback(
    Output('gauge-graphs', 'children'),
    [Input('gauge-graphs', 'children')]
)

def update_gauges_graphs(_):
    data, timestamps = get_data(start_date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'))
    
    # Define variable properties
    variables = {
        'temperaturaaire': {'name': 'Temperatura Aire', 'range': [-50, 100], 'unit': '°C', 'colors': {'normal': 'green', 'warning': 'yellow', 'danger': 'red'}, 'icon': '/assets/temperature_icon.png', 'thresholds': [10, 25, 50]},
        'humedadaire': {'name': 'Humedad Aire', 'range': [0, 100], 'unit': '%', 'colors': {'normal': 'green', 'warning': 'yellow', 'danger': 'red'}, 'icon': '/assets/humidity_icon.png', 'thresholds': [20, 60, 80]},
        'intensidadluz': {'name': 'Intensidad Luz', 'range': [0, 50000], 'unit': 'lux', 'colors': {'normal': 'green', 'warning': 'yellow', 'danger': 'red'}, 'icon': '/assets/light_icon.png', 'thresholds': [10000, 25000, 50000]},
        'indiceuv': {'name': 'Índice UV', 'range': [0, 30], 'unit': '', 'colors': {'normal': 'green', 'warning': 'yellow', 'danger': 'red'}, 'icon': '/assets/uv_icon.png', 'thresholds': [4, 14, 25]},
        'velocidadviento': {'name': 'Velocidad Viento', 'range': [0, 10], 'unit': 'm/s', 'colors': {'normal': 'green', 'warning': 'yellow', 'danger': 'red'}, 'icon': '/assets/wind_speed_icon.png', 'thresholds': [3, 5, 8]},
        'cantidadlluvia': {'name': 'Cantidad Lluvia', 'range': [0, 30], 'unit': 'mm/h', 'colors': {'normal': 'green', 'warning': 'yellow', 'danger': 'red'}, 'icon': '/assets/rain_icon.png', 'thresholds': [10, 20, 30]},
    }
    
    gauges_graphs = []
    for variable, props in variables.items():
        # Obtener el último valor de la variable
        last_value = data[variable][-1] if data[variable] else 0
        
        # Determinar el color del gauge
        if variable == 'temperaturaaire':
            if last_value > 30:
                color = props['colors']['danger']
            elif last_value > 25:
                color = props['colors']['warning']
            else:
                color = props['colors']['normal']
        elif variable == 'humedadaire':
            if last_value > 80:
                color = props['colors']['danger']
            elif last_value > 60:
                color = props['colors']['warning']
            else:
                color = props['colors']['normal']
        elif variable == 'intensidadluz':
            if last_value > 50000:
                color = props['colors']['danger']
            elif last_value > 20000:
                color = props['colors']['warning']
            else:
                color = props['colors']['normal']
        elif variable == 'indiceuv':
            if last_value > 25:
                color = props['colors']['danger']
            elif last_value > 14:
                color = props['colors']['warning']
            else:
                color = props['colors']['normal']
        elif variable == 'velocidadviento':
            if last_value > 8:
                color = props['colors']['danger']
            elif last_value > 5:
                color = props['colors']['warning']
            else:
                color = props['colors']['normal']
        elif variable == 'cantidadlluvia':
            if last_value > 30:
                color = props['colors']['danger']
            elif last_value > 20:
                color = props['colors']['warning']
            else:
                color = props['colors']['normal']

        # Crear gauge
        gauge = dcc.Graph(
            id=f'gauge-{variable}',
            figure={
                'data': [go.Indicator(
                    mode="gauge+number",
                    value=last_value,
                    gauge={'axis': {'range': props['range']}, 'bar': {'color': color}},
                    title={'text': f"{props['name']} ({props['unit']})"}
                )],
                'layout': go.Layout(
                    height=400,
                    width=400,
                    margin=dict(l=0, r=0, t=40, b=0),
                    images=[
                        dict(
                            source=props['icon'],
                            x=0.5,
                            y=0.5,
                            sizex=0.1,  # Tamaño más pequeño
                            sizey=0.1,  # Tamaño más pequeño
                            xanchor='center',
                            yanchor='middle'
                        )
                    ]
                )
            }
        )
        
        # Crear gráfico de líneas
        chart = dcc.Graph(
            id=f'chart-{variable}',
            figure={
                'data': [go.Scatter(
                    x=timestamps,
                    y=data[variable],
                    mode='lines+markers',
                    line={'color': props['colors']['normal']}
                )],
                'layout': go.Layout(
                    height=400,
                    width=800,
                    title=f'{props["name"]} vs Tiempo',
                    xaxis_title='Fecha',
                    yaxis_title=f'{props["name"]} ({props["unit"]})',
                    title_x=0.5,
                    title_y=0.85,
                    shapes=[
                        dict(
                            type='line',
                            x0=timestamps[0],
                            x1=timestamps[-1],
                            y0=props['thresholds'][0],
                            y1=props['thresholds'][0],
                            line=dict(color='blue', width=2, dash='dash'),
                            name='Riesgo'
                        ),
                        dict(
                            type='line',
                            x0=timestamps[0],
                            x1=timestamps[-1],
                            y0=props['thresholds'][1],
                            y1=props['thresholds'][1],
                            line=dict(color='blue', width=2, dash='dash'),
                            name='Óptimo'
                        ),
                        dict(
                            type='line',
                            x0=timestamps[0],
                            x1=timestamps[-1],
                            y0=props['thresholds'][2],
                            y1=props['thresholds'][2],
                            line=dict(color='blue', width=2, dash='dash'),
                            name='Dañino'
                        )
                    ],
                    annotations=[
                        dict(
                            xref='paper', yref='y',
                            x=0.05, y=props['thresholds'][0],
                            text='Riesgo',
                            showarrow=False,
                            font=dict(size=12, color='blue')
                        ),
                        dict(
                            xref='paper', yref='y',
                            x=0.05, y=props['thresholds'][1],
                            text='Óptimo',
                            showarrow=False,
                            font=dict(size=12, color='blue')
                        ),
                        dict(
                            xref='paper', yref='y',
                            x=0.05, y=props['thresholds'][2],
                            text='Dañino',
                            showarrow=False,
                            font=dict(size=12, color='blue')
                        )
                    ]
                )
            }
        )

        gauges_graphs.append(html.Div([gauge, chart], style={'display': 'flex', 'margin-bottom': '20px'}))
    return gauges_graphs


@app.callback(
    Output('custom-graph', 'figure'),
    [Input('variable-selector', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_custom_graph(selected_vars, start_date, end_date):
    if not selected_vars:
        return go.Figure()
    
    data, timestamps = get_data(start_date, end_date)
    
    # Define variable properties
    variables = {
        'temperaturaaire': {'name': 'Temperatura Aire', 'color': 'blue', 'unit': '°C'},
        'humedadaire': {'name': 'Humedad Aire', 'color': 'brown', 'unit': '%'},
        'intensidadluz': {'name': 'Intensidad Luz', 'color': 'orange', 'unit': 'lux'},
        'indiceuv': {'name': 'Índice UV', 'color': 'purple', 'unit': ''},
        'velocidadviento': {'name': 'Velocidad Viento', 'color': 'green', 'unit': 'km/h'},
       #'direccionviento': {'name': 'Dirección Viento', 'color': 'red', 'unit': '°'},
        'cantidadlluvia': {'name': 'Cantidad Lluvia', 'color': 'cyan', 'unit': 'mm'},
      # 'presionbarometrica': {'name': 'Presión Barométrica', 'color': 'magenta', 'unit': 'hPa'}
    }
    
    fig = go.Figure()
    
    if len(selected_vars) == 1:
        variable = selected_vars[0]
        if variable in data:
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=data[variable],
                mode='lines+markers',
                name=variables[variable]['name'],
                line={'color': variables[variable]['color']}
            ))
            fig.update_layout(
                title=f'{variables[variable]["name"]} vs Tiempo',
                xaxis_title='Fecha',
                yaxis_title=f'{variables[variable]["name"]} ({variables[variable]["unit"]})',
                title_x=0.5,
                shapes=[
                    dict(
                        type='line',
                        x0=timestamps[0],
                        x1=timestamps[-1],
                        y0=variables[variable]['thresholds'][0],
                        y1=variables[variable]['thresholds'][0],
                        line=dict(color='blue', width=2, dash='dash'),
                        name='Riesgo',
                        layer='below'
                    ),
                    dict(
                        type='line',
                        x0=timestamps[0],
                        x1=timestamps[-1],
                        y0=variables[variable]['thresholds'][1],
                        y1=variables[variable]['thresholds'][1],
                        line=dict(color='blue', width=2, dash='dash'),
                        name='Óptimo',
                        layer='below'
                    ),
                    dict(
                        type='line',
                        x0=timestamps[0],
                        x1=timestamps[-1],
                        y0=variables[variable]['thresholds'][2],
                        y1=variables[variable]['thresholds'][2],
                        line=dict(color='blue', width=2, dash='dash'),
                        name='Daño',
                        layer='below'
                    )
                ],
                annotations=[
                    dict(
                        xref='paper', yref='y',
                        x=0.05, y=variables[variable]['thresholds'][0],
                        text=variables[variable]['threshold_labels'][0],
                        showarrow=False,
                        font=dict(size=12, color='blue')
                    ),
                    dict(
                        xref='paper', yref='y',
                        x=0.05, y=variables[variable]['thresholds'][1],
                        text=variables[variable]['threshold_labels'][1],
                        showarrow=False,
                        font=dict(size=12, color='blue')
                    ),
                    dict(
                        xref='paper', yref='y',
                        x=0.05, y=variables[variable]['thresholds'][2],
                        text=variables[variable]['threshold_labels'][2],
                        showarrow=False,
                        font=dict(size=12, color='blue')
                    )
                ]
            )
    
    elif len(selected_vars) == 2:
        var1, var2 = selected_vars
        if var1 in data and var2 in data:
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=data[var1],
                mode='lines+markers',
                name=variables[var1]['name'],
                line={'color': variables[var1]['color']},
                yaxis='y1'
            ))
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=data[var2],
                mode='lines+markers',
                name=variables[var2]['name'],
                line={'color': variables[var2]['color']},
                yaxis='y2'
            ))
            fig.update_layout(
                title='Gráfico Personalizado',
                xaxis_title='Fecha',
                yaxis_title=f'{variables[var1]["name"]} ({variables[var1]["unit"]})',
                yaxis2=dict(
                    title=f'{variables[var2]["name"]} ({variables[var2]["unit"]})',
                    overlaying='y',
                    side='right'
                ),
                title_x=0.5
            )
    
    else:
        for variable in selected_vars:
            if variable in data:
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=data[variable],
                    mode='lines+markers',
                    name=variables[variable]['name'],
                    line={'color': variables[variable]['color']}
                ))
        fig.update_layout(
            title='Gráfico Personalizado',
            xaxis_title='Fecha',
            yaxis_title='Valor',
            legend_title='Variables',
            title_x=0.5
        )
    
    return fig
    
if __name__ == '__main__':
      app.run(port=8080)                                                                
