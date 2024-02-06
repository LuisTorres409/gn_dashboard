import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd
import folium
import requests
from datetime import datetime
import re
from streamlit_extras.app_logo import add_logo
from streamlit_folium import st_folium


st.set_page_config(layout='wide')

regions_dict = {'Norte': ['AM','PA','AC','AP','RO','RR','TO'],
           'Sul' : ['SC','RS','PR'],
           'Sudeste' : ['RJ','SP','MG','ES'],
           'Nordeste' : ['BA','CE','MA','PB','PE','PI','RN','SE'],
           'Centro-Oeste' : ['DF','GO','MT','MS']}

states = ['AM','PA','AC','AP','RO','RR','TO','SC','RS','PR','RJ','SP','MG','ES','BA','CE','MA','PB','PE','PI','RN','SE','DF','GO','MT','MS']

regions = ['Norte','Sul','Sudeste','Nordeste','Centro-Oeste']

codigos_estados = [
    13, 15, 12, 16, 11, 14, 17, 42, 43, 41,
    33, 35, 31, 32, 29, 23, 21, 25, 26, 22,
    24, 28, 53, 52, 51, 50
]

codigos_regioes = [1,4,3,2,5]


def extrair_estado(nome_distribuidora):
    match = re.search(r'\((\w+)\)$', nome_distribuidora)
    if match:
        return match.group(1)
    else:
        return None

@st.cache_data
def get_data(filename):
    df = pd.read_excel(filename,sheet_name='2008-2023')
    df = df.T
    num_colunas = df.shape[1]
    for i in range(num_colunas):
        df = df.rename(columns={i: df.iloc[0,i]})
    df = df.rename(columns={'CONSUMO DE GÁS NATURALPOR DISTRIBUIDORA SEM O SEGMENTO TERMELÉTRICO (em milhões de m³/dia)':'Data','TOTAL DISTRIBUIDORAS SEM O SEGMENTO TERMELÉTRICO':'Demanda total nacional'})
    df = df.drop(df.index[0])
    df = df.reset_index(drop=True)
    df['Data'] = pd.to_datetime(df['Data'], format='%Y-%m')
    return df

@st.cache_data
def get_percentuals_distribuidoras(df_filtered_year):
    
    media_nacional = df_filtered_year['Demanda total nacional'].mean()

    percentuals = []
    distribuidoras_percentuals = distribuidoras[:-1]

    for distribuidora_loop in distribuidoras[:-1]:
        percentual_nacional = (df_filtered_year[distribuidora_loop].mean()/media_nacional)*100
        percentuals.append(percentual_nacional)

    dados = {'Distribuidora' : distribuidoras_percentuals,
             'Percentual demanda GN' : percentuals}

    df_percentuals = pd.DataFrame(dados)

    return df_percentuals
    
@st.cache_data
def get_percentuals_regions(df_filtered_year):
    
    media_nacional = df_filtered_year['Demanda total nacional'].mean()

    percentuals_dict = {'Norte': 0,
           'Sul' : 0,
           'Sudeste' : 0,
           'Nordeste' :0,
           'Centro-Oeste' : 0}

    for distribuidora_loop in distribuidoras[:-1]:
        percentual_nacional = (df_filtered_year[distribuidora_loop].mean()/media_nacional)*100
        state = distribuidora_loop.split('(')[1].strip()[:-1]
        for region, states in regions_dict.items():
            if state in states:
                percentuals_dict[region] += percentual_nacional
    
    dados = {'Regiao' : list(percentuals_dict.keys()),
             'Percentual demanda GN' : list(percentuals_dict.values())}

    df_percentuals = pd.DataFrame(dados)

    return df_percentuals

@st.cache_data
def get_states():
    response = requests.get(url = 'https://raw.githubusercontent.com/fititnt/gis-dataset-brasil/master/uf/geojson/uf.json')
    if response.status_code == 200: # O código 200 (OK) indica que a solicitação foi bem sucedida
        state_geo = response.json()
        return state_geo

@st.cache_data
def get_regions():
    response = requests.get(url = f'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=maxima&intrarregiao=regiao')
    return response.json()

df = get_data('Demanda GN sem Termelétrica.xlsx')

distribuidoras = df.columns[1:]

lista_cores = ['#000000' for _ in range(len(distribuidoras)-1)]

colors_dict = dict(zip(distribuidoras,lista_cores))

st.sidebar.image('epe_logo.png',width=120)

st.sidebar.header('Escolha os filtros')

filter_options = ['Distribuidora','Região']

filter = st.sidebar.radio('Filtros',filter_options)

anos_disponiveis_string = df['Data'].dt.strftime('%Y').unique()

anos_disponiveis = [eval(i) for i in anos_disponiveis_string]

# Input para escolher um range de anos
anos_escolhidos = st.sidebar.slider("Escolha o intervalo de anos",
                                min_value=min(anos_disponiveis),
                                max_value=max(anos_disponiveis),
                                value=(anos_disponiveis[0], anos_disponiveis[-1]),
                                step=1)
anos_escolhidos = list(range(anos_escolhidos[0], anos_escolhidos[1] + 1))
anos_escolhidos_string = [str(i) for i in anos_escolhidos]

df_filtered_year = df[df['Data'].dt.strftime('%Y').isin(anos_escolhidos_string)]
datas = df_filtered_year['Data']

if filter == 'Distribuidora':
    distribuidora = st.sidebar.multiselect('Distribuidora',distribuidoras,placeholder='Escolha a distribuidora')

    if not distribuidora:
        st.sidebar.error("Escolha as distribuidoras")

        states_geo = get_states()
        map = folium.Map(
        location=[-14.2350,-51.9253],
        tiles='cartodbpositron',
        zoom_start=4,
        )

        # DataFrame vazio para armazenar os dados agrupados por estados
        df_estados = pd.DataFrame()

        # Iterar sobre os estados
        for estado in states:
            # Filtrar as colunas dos estados pertencentes a esse estado
            colunas_estado = [coluna for coluna in df_filtered_year.columns if extrair_estado(coluna) == estado]
            # Somar os valores das colunas do estado
            df_estados[estado] = df_filtered_year[colunas_estado].sum(axis=1)

        # Adicionar uma coluna de data ao novo DataFrame
        df_estados['Data'] = df_filtered_year['Data']

        df_estados = pd.DataFrame(df_estados.mean())
        
        df_estados = df_estados.iloc[:-1]

        df_estados = df_estados.rename(columns={0:'Demanda GN'})

        df_estados['Código'] = codigos_estados
        df_estados['Código'] = df_estados['Código'].astype(str)

        estados = df_estados.index

        df_estados['UFs'] = estados

        df_estados.reset_index(drop=True,inplace=True)


        #Colorindo o mapa
        folium.Choropleth(
            geo_data=states_geo, #contorno dos estados
            data=df_estados, #dados de população
            columns=['Código', 'Demanda GN'], #colunas do dataframe state_data com o código e a população de cada estado
            key_on='feature.properties.GEOCODIGO', #propriedade do state_geo que contém o código de cada estado
            fill_color='YlOrRd', #‘BuGn’, ‘BuPu’, ‘GnBu’, ‘OrRd’, ‘PuBu’, ‘PuBuGn’, ‘PuRd’, ‘RdPu’, ‘YlGn’, ‘YlGnBu’, ‘YlOrBr’, and ‘YlOrRd’.
            fill_opacity=0.7, #opacidade do preenchimento (cor) de cada estado
            line_opacity=0.5, #opacidade da linha que define cada estado
            line_color='black', #cor da linha que define cada estado
            highlight=True, #destaca o estado ao passar com o mouse em cima dele
            legend_name='Demanda de GN', #nome da legenda
            threshold_scale=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
        ).add_to(map)

        st.title(f'Mapa de calor da Demanda de GN {min(anos_escolhidos)} - {max(anos_escolhidos)} por estado')

        st_folium(map,width=1500)


    else:

        df_filtered_distribuidora = df_filtered_year[distribuidora]
        df_filtered_distribuidora = pd.concat([df_filtered_distribuidora,datas],axis=1)

        demandas_distribuidora = px.line(df_filtered_year, x='Data', y=distribuidora, title=f'Demanda de GN em {min(anos_escolhidos)} - {max(anos_escolhidos)}',height=430, width=400,
                                        labels={'value':'Demanda GN em milhões de m³/dia'})
        demandas_distribuidora.update_traces(line_width=3)
        demandas_distribuidora.update_layout(yaxis=dict(title_text="Distribuidoras"))
        st.plotly_chart(demandas_distribuidora,use_container_width=True)

        cores_distribuidoras = [trace['line']['color'] for trace in demandas_distribuidora.data]        
       
        df_percentuals = get_percentuals_distribuidoras(df_filtered_year)

        cores_distribuidoras_dict = dict(zip(distribuidora, cores_distribuidoras))

        percentuals_chart = px.bar(df_percentuals,x = 'Distribuidora',y = 'Percentual demanda GN',height=430, width=400,title = f'Percentual de cada distribuidora em relação ao total nacional {min(anos_escolhidos)} - {max(anos_escolhidos)}',
                                hover_data=['Percentual demanda GN'])
        percentuals_chart.update_traces(marker=dict(color=[cores_distribuidoras_dict[dist] if dist in distribuidora else '#000000' for dist in distribuidoras[:-1]]))
        st.plotly_chart(percentuals_chart,use_container_width=True)  



elif filter == 'Região':
    regions_selected = st.sidebar.multiselect('Região',regions,placeholder='Escolha a região')
    
    if not regions_selected:
        st.sidebar.error("Escolha as distribuidoras")

        regions_geo = get_regions()
        #st.write(regions_geo)
        map = folium.Map(
        location=[-14.2350,-51.9253],
        tiles='cartodbpositron',
        zoom_start=4,
        )

        df_regioes = pd.DataFrame()

        # Iterar sobre as regiões
        for regiao, estados in regions_dict.items():
            # Filtrar as colunas dos estados pertencentes a essa região e extrair o estado de cada coluna
            colunas_regiao = [coluna for coluna in df_filtered_year.columns if extrair_estado(coluna) in estados]
            # Agrupar as colunas dos estados pertencentes a essa região e somar os valores das colunas
            df_regioes[regiao] = df_filtered_year[colunas_regiao].sum(axis=1)

        # Adicionar uma coluna de data ao novo DataFrame
        df_regioes['Data'] = df_filtered_year['Data']
        
        df_regioes_filtrado = df_regioes[[regiao for regiao in regions if regiao in df_regioes.columns]]
        df_regioes_filtrado = pd.concat([df_regioes_filtrado,datas],axis=1)

        df_regioes = pd.DataFrame(df_regioes.mean())
        
        df_regioes = df_regioes.iloc[:-1]

        df_regioes = df_regioes.rename(columns={0:'Demanda GN'})
        df_regioes['Código'] = codigos_regioes

        regioes = df_regioes.index

        df_regioes['Regioes'] = regioes

        df_regioes.reset_index(drop=True,inplace=True)

        #Colorindo o mapa
        folium.Choropleth(
            geo_data=regions_geo, #contorno dos estados
            data=df_regioes, #dados de população
            columns=['Código', 'Demanda GN'], #colunas do dataframe state_data com o código e a população de cada estado
            key_on='feature.properties.codarea', #propriedade do state_geo que contém o código de cada estado
            fill_color='YlOrRd', #‘BuGn’, ‘BuPu’, ‘GnBu’, ‘OrRd’, ‘PuBu’, ‘PuBuGn’, ‘PuRd’, ‘RdPu’, ‘YlGn’, ‘YlGnBu’, ‘YlOrBr’, and ‘YlOrRd’.
            fill_opacity=0.7, #opacidade do preenchimento (cor) de cada estado
            line_opacity=0.5, #opacidade da linha que define cada estado
            line_color='black', #cor da linha que define cada estado
            highlight=True, #destaca o estado ao passar com o mouse em cima dele
            legend_name='Demanda de GN', #nome da legenda
        ).add_to(map)

        st.title(f'Mapa de calor da Demanda de GN {min(anos_escolhidos)} - {max(anos_escolhidos)} por região')

        st_folium(map,width=1500)

    else:

        # Criar um novo DataFrame com as colunas das regiões do país
        df_regioes = pd.DataFrame()

        # Iterar sobre as regiões
        for regiao, estados in regions_dict.items():
            # Filtrar as colunas dos estados pertencentes a essa região e extrair o estado de cada coluna
            colunas_regiao = [coluna for coluna in df_filtered_year.columns if extrair_estado(coluna) in estados]
            # Agrupar as colunas dos estados pertencentes a essa região e somar os valores das colunas
            df_regioes[regiao] = df_filtered_year[colunas_regiao].sum(axis=1)

        # Adicionar uma coluna de data ao novo DataFrame
        df_regioes['Data'] = df_filtered_year['Data']
        
        df_regioes_filtrado = df_regioes[[regiao for regiao in regions if regiao in df_regioes.columns]]
        df_regioes_filtrado = pd.concat([df_regioes_filtrado,datas],axis=1)

        demandas_region = px.line(df_regioes_filtrado, x='Data', y=regions_selected, title=f'Demanda de GN em {min(anos_escolhidos)} - {max(anos_escolhidos)}',height=430, width=400,
                                        labels={'value':'Demanda GN em milhões de m³/dia'})
        demandas_region.update_traces(line_width=3) 
        st.plotly_chart(demandas_region,use_container_width=True)

        cores_regions = [trace['line']['color'] for trace in demandas_region.data]

        cores_regions_dict = dict(zip(regions_selected, cores_regions))

        df_percentuals = get_percentuals_regions(df_filtered_year)

        percentuals_chart = px.bar(df_percentuals,x = 'Regiao',y = 'Percentual demanda GN',height=430, width=400,title = f'Percentual de cada region em relação ao total nacional {min(anos_escolhidos)} - {max(anos_escolhidos)}',
                                hover_data=['Percentual demanda GN'])
        percentuals_chart.update_traces(marker=dict(color=[cores_regions_dict[reg] if reg in cores_regions_dict else '#000000' for reg in regions]))

        st.plotly_chart(percentuals_chart,use_container_width=True)
