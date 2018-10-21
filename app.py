import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.plotly as py
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime as dt
from time import gmtime, localtime

from scrap import getLaunches, geocode
import requests
import bs4

def get_image(query):
    pquery = query.replace(' ', '+')
    soup = bs4.BeautifulSoup(requests.get(f"https://google.com/search?q={pquery}&tbm=isch").text, 'lxml')
    for img in soup.select("img[alt]"):
        if query in img["alt"]:
             return img["src"]
    

mapbox_access_token = 'pk.eyJ1IjoiYW5kcmV5ZGVuIiwiYSI6ImNqbmhwdGlkMjBhYzQzanJzbTM3NzdobW8ifQ.ZR_vrBuTDB1-byVDkuxn4g'
mapbox_style = 'mapbox://styles/redboot/cjnidreh14o5o2rs1vgnsol2p'

rockets = pd.read_excel('Rockets and spaceports.xlsx', 'Rockets')
spaceports = pd.read_excel('Rockets and spaceports.xlsx', 'Spaceports')

for index, row in rockets.iterrows():
    if pd.isnull(row["Rocket"]): continue
    row["Photo"] = get_image("Rocket "+row["Rocket"])

print("done.")

past = getLaunches(True)
to_be_launched = getLaunches()
launches = pd.DataFrame(data=past+to_be_launched)
launches = launches[~launches['lat'].isna()]

density = launches['lat'].value_counts()
launches['same'] = launches['lat'].apply(lambda x: density[x])

app = dash.Dash(__name__)

app.css.append_css({
   'external_url': (
       'main.css'
   )
})

def render_rocket(idx, row):
    if pd.isnull(row.values).any(): 
        return ''
    return html.Div(
        className="rocketinfo",
        children=[
            html.Div(
                className="top",
                children=[html.H1(f"Rocket #{int(idx+1)}" + ": "+row['Rocket'])],
            ),
            html.Div(
                className="bottom",
                children=[
                    html.Img(src=row["Photo"]),
                    html.Div(
                        className="text",
                        children=[
                            html.P(children=[html.B(children=k), ': '+ str(v)])
                            for k, v in row.items()
                            if k in ['Company', 'Site', 'Country'] and str(v).lower() != "nan"
                        ]
                    )
                ]
            )
        ]
    )

def divTemplate(idx, row):
    return html.Div(
        className="launch",
        children=[
            html.Div(
                className="top",
                children=[html.H1(f"Mission #{idx+1}" + ": "+row['mission'])],
            ),
            html.Div(
                className="bottom",
                children=[
                    html.Img(src=row['image']),
                    html.Div(className="text",
                    children=[
                        html.Div(
                            className="info",
                            children=[
                                html.P(children=[html.B(children=k.capitalize()), ': '+ str(v)])
                                for k, v in row.items()
                                if k in ['vehicle', 'time', 'location', 'pad', 'window'] and str(v) != "nan"
                            ]
                        ),
                        html.Div(
                            className="description",
                            children=row['description'],
                        )
                    ])

                ]
            )
        ]
    )

index_page = [
    dcc.Link('Home', href='/home'),
    html.Br(),
    dcc.Link('Rockets', href='/rockets')
]

main_page = [
    dcc.Link('Rockets', id='rockets', className='ref', href='/rockets'),
    html.Div(id='temp'),
    html.A(href="https://clever-boyd-6ef0a3.netlify.com/", className='ref', children="Info"),
    html.H1(id='name', children='LAUNCH.IO'),
    html.H1(id='Timer',children='0'),
    html.Div([
        dcc.Graph(
            id='map',
            figure=go.Figure(
                data=[
                    go.Scattermapbox(
                        lat=launches['lat'].unique(),
                        lon=launches['long'].unique(),
                        mode='markers',
                        opacity=0.7,
                        marker=dict(
                            sizemin=10,
                            size=launches['same']*3,
                            color='limegreen'
                        ),
                        hoverinfo='text',
                        hoverlabel={"font": {"size": 14}},
                        text=launches['location'].unique(),
                )],
                layout=go.Layout(
                    hovermode='closest',
                    paper_bgcolor="rgb(0, 31, 31)",
                    margin=go.layout.Margin(
                        l=10,
                        r=10,
                        b=0,
                        t=0,
                        pad=8
                    ),
                    mapbox=dict(
                        accesstoken=mapbox_access_token,
                        style=mapbox_style,
                        bearing=0,
                        center=dict(
                            lat=45,
                            lon=-73
                        ),
                        pitch=0,
                        zoom=2
                    )
                )
            ),
            config={'displayModeBar': False}
        )
    ]),
    html.Div(
        dcc.Interval(
            id='interval-component',
            interval=1000,
            n_intervals=0
        )
    ),
    html.Div([
        dcc.Tabs(id="tabs", className="tabs", value='tab-2', children=[
            dcc.Tab(label='This location', value='tab-1', className='tab', selected_className="tab-selected"),
            dcc.Tab(label='ALL', value='tab-2', className='tab', selected_className="tab-selected"),
        ]),
        html.Div(
            id='rocket',
            children=[divTemplate(index, row) for index, row in launches.iterrows()]
        )
    ])
]

rockets_page = [html.Div(html.H1("Rockets list", className="title"))]+[render_rocket(index, row) for index, row in rockets.iterrows()]

app.config.suppress_callback_exceptions = True

app.layout = html.Div(
    children=[
        dcc.Location(id='url', refresh=False),
        html.Div(className='main', id='Main')
    ]
)

@app.callback(Output('Main', 'children'),
              [Input('url', 'pathname')])
def displayRocketList(path_name):
    if path_name == '/':
        return main_page
    elif path_name == '/rockets':
        return rockets_page
    else:
        return index_page

@app.callback(Output('rocket', 'children'),
              [Input('map', 'clickData'), Input('tabs', 'value')])
def update_on_click(clickData, tab):
    if tab == 'tab-1':
        if not clickData:
            return html.Div(style={'height': "1000px"})
        launch = launches[launches['lat'] == clickData['points'][0]['lat']]
        return [divTemplate(index, row) for index, row in launch.iterrows()]
    elif tab == 'tab-2':
        return [divTemplate(index, row) for index, row in launches.iterrows()]

@app.callback(Output('Timer', 'children'),
              [Input('interval-component', 'n_intervals')])
def timeToNearestLaunch(n):
    T = to_be_launched[0]['time']
    T = T[-20:-1]

    diff = dt.strptime(T, '%Y-%m-%d %H:%M:%S') - dt.utcnow()
    tz_diff = localtime().tm_hour - gmtime().tm_hour #(gmtime().tm_day - localtime().tm_day)*24
    full_seconds = 24*3600*diff.days
    hours = int((full_seconds-diff.seconds)/3600/24) - tz_diff
    minutes = int((diff.seconds-hours*60)/60/24)
    return 'Next launch: {} days {} hours {} minutes {} seconds'.format(diff.days,
                                                                   hours,
                                                                   minutes,
                                                                   diff.seconds%60)

if __name__ == '__main__':
    #app.scripts.config.serve_locally = False
    app.run_server()
