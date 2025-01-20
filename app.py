import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import pandas as pd
import plotly.graph_objects as go

##################################################
#                                                #
#                    SETTINGS                    #
#                                                #
##################################################

st.set_page_config(layout='wide', page_title='Timeseries Viz')

##################################################
#                                                #
#                 SESSION STATES                 #
#                                                #
##################################################

if 'dataset' not in st.session_state:
    st.session_state['dataset'] = pd.DataFrame()
if 'generate_report' not in st.session_state:
    st.session_state['generate_report'] = False
if 'ath_col_unique' not in st.session_state:
    st.session_state['ath_col_unique'] = ''

#################################################
#                                               #
#                   FUNCTIONS                   #
#                                               #
#################################################

def load_file():
    try:
        try:
            st.session_state['dataset'] = pd.read_csv(st.session_state['file'])
            st.session_state['col_options'] = st.session_state['dataset'].columns
            st.session_state['ath_col_options'] = st.session_state['col_options']
        except:
            st.session_state['dataset'] = pd.read_excel(st.session_state['file'])
            st.session_state['col_options'] = st.session_state['dataset'].columns
            st.session_state['ath_col_options'] = st.session_state['col_options']
    except:
        st.session_state['dataset'] = pd.DataFrame()

def plot(data, date_col, feature, ath_col='', ath=''):
    if (ath_col != '') and (ath != ''):
        data_g = data[data[ath_col]==ath].copy()
        title_ = f'{ath} - {feature}'
    else:
        data_g = data.copy()
        title_ = feature

    fig = go.Figure()
    fig.add_trace(go.Bar(x=data_g[date_col], y=data_g[feature], opacity=.3,
                         marker=dict(color='#f7f9f8', line_color='blue', line_width=.2), name=feature))
    fig.add_trace(go.Scatter(x=data_g[date_col], y=data_g[f'{feature}_tc'],
                             mode='lines', line=dict(shape='spline', color='red', width=2),
                             name='Immediate effects'))
    fig.add_trace(go.Scatter(x=data_g[date_col], y=data_g[f'{feature}_tl'],
                             mode='lines', line=dict(shape='spline', color='green', width=2),
                             name='Delayed cumulative effects'))
    
    fig.update_layout(hovermode='x', height=300, title=title_,
                      legend=dict(orientation='h', yanchor='bottom', xanchor='right', y=1.01, x=1),
                      margin=dict(l=10, r=10, b=50, t=40),
                      paper_bgcolor='rgba(0, 0, 0, 0)', plot_bgcolor='rgba(0, 0, 0, 0)')
    return fig

def load_report():
    st.session_state['dataset'][st.session_state['date_col']] = pd.to_datetime(st.session_state['dataset'][st.session_state['date_col']])
    st.session_state['data_report'] = st.session_state['dataset'].sort_values(by=[st.session_state['date_col']], ignore_index=True)

    if st.session_state['groupby_date']:
        agg_dict = {f: st.session_state[f'{f}_agg'] for f in st.session_state['features_col']}

        st.session_state['data_report'] = (st.session_state['data_report']
                                           .groupby([st.session_state['ath_col'], st.session_state['date_col']], as_index=False).agg(agg_dict))
    
    if st.session_state['ath_dataset']:
        for f in st.session_state['features_col']:
            st.session_state['data_report'][f'{f}_tc'] = (st.session_state['data_report']
                                                          .groupby(st.session_state['ath_col'], as_index=False)[f]
                                                          .transform(lambda x: x.rolling(st.session_state['tc_days'], min_periods=2)
                                                                     .quantile(.5).ewm(span=st.session_state['tc_days'], adjust=False)
                                                                     .mean()))
            st.session_state['data_report'][f'{f}_tl'] = (st.session_state['data_report']
                                                          .groupby(st.session_state['ath_col'], as_index=False)[f]
                                                          .transform(lambda x: x.rolling(st.session_state['tl_days'], min_periods=2)
                                                                     .quantile(.5).ewm(span=st.session_state['tl_days'], adjust=False)
                                                                     .mean()))
            for a in st.session_state['data_report'][st.session_state['ath_col']].unique():
                st.session_state[f'{a}_{f}_graph'] = plot(st.session_state['data_report'],
                                                          st.session_state['date_col'],
                                                          f,
                                                          st.session_state['ath_col'], a)
                
        st.session_state['data_download'] = pd.merge(st.session_state['dataset'], st.session_state['data_report'],
                                                     on=[st.session_state['ath_col'], st.session_state['date_col']])
    else:
        for f in st.session_state['features_col']:
            st.session_state['data_report'][f'{f}_tc'] = (st.session_state['data_report'][f]
                                                          .rolling(st.session_state['tc_days'], min_periods=1)
                                                          .quantile(.5).ewm(span=st.session_state['tc_days']).mean())
            st.session_state['data_report'][f'{f}_tl'] = (st.session_state['data_report'][f]
                                                          .rolling(st.session_state['tl_days'], min_periods=1)
                                                          .quantile(.5).ewm(span=st.session_state['tl_days']).mean())

            st.session_state[f'{f}_graph'] = plot(st.session_state['data_report'],
                                                  st.session_state['date_col'],
                                                  f)
            
        st.session_state['data_download'] = pd.merge(st.session_state['dataset'], st.session_state['data_report'],
                                                     on=[st.session_state['date_col']])
    st.session_state['generate_report'] = True
    st.session_state['ath_col_options'] = [st.session_state['ath_col']]

#################################################
#                                               #
#                    SIDEBAR                    #
#                                               #
#################################################

with st.sidebar:
    st.image('img/settings2.png', width=75,)
    with st.expander('Dataset'):
        st.file_uploader('Options: .csv .xls .xlsx', key='file', on_change=load_file)

    if not st.session_state['dataset'].empty:
        st.selectbox('Date column', options=st.session_state['col_options'], index=0, key='date_col')
        st.checkbox('Multiple data entries/rows for a same date', key='groupby_date')

        st.multiselect('Features to plot', options=st.session_state['col_options'], key='features_col')
        if st.session_state['groupby_date']:
            with st.expander('Daily aggregation', expanded=True):
                st.caption('Select the aggregation for daily value for each feature')
                for f in st.session_state['features_col']:
                    st.selectbox(f, options=['sum', 'median'], index=1, key=f'{f}_agg')

        st.write('---')
        st.caption('Choose the number of days for the short and long trends')
        st.number_input('Short trend (immediate effects)', min_value=1, key='tc_days')
        st.number_input('Long trend (delayed cumulative effects)', min_value=1, key='tl_days')
        st.write('---')
        st.checkbox('Team dataset (multiple athletes)', key='ath_dataset')

        if st.session_state['ath_dataset']:
            st.selectbox('Athlete Name column', options=st.session_state['ath_col_options'], index=0, key='ath_col')
        st.write('---')
        with stylable_container(
            key='settings_btn', css_styles="""button {
                background-color: green; color: white;}
                """,): st.button('Load Report', on_click=load_report)

    st.write('')
    st.write('---')
    ccredits = st.columns([.7, .3], vertical_alignment='center')
    with ccredits[0]:
        st.caption('Developped by [Raphaël Lagarde](https://www.linkedin.com/in/raphael-lagarde-511b40100/)')
    with ccredits[1]: 
        st.image('img/logo_LinkedIn2.png', width=25)

################################################
#                                              #
#                    REPORT                    #
#                                              #
################################################
with stylable_container(
        key='container_title',
        css_styles="""
            {border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 0.5rem;
            padding: calc(1em - 1px);
            background-color: #2e2f33}"""):
    ctitle = st.columns([.25, .1, .65], vertical_alignment='center')
    with ctitle[1]:
        st.image('img/tm.png', width=75)
    with ctitle[2]:
        st.title('Timeseries report')
    st.write('')

st.write('')
st.write('')
if (st.session_state['generate_report']) and (st.session_state['ath_dataset']):
    tabs = st.tabs(list(st.session_state['data_report'][st.session_state['ath_col']].unique()))

    for i, ath in enumerate(list(st.session_state['data_report'][st.session_state['ath_col']].unique())):
        with tabs[i]:
            for f in st.session_state['features_col']:
                with stylable_container(
                    key=f'{ath}_{f}container_title',
                    css_styles="""
                        {display: flex;
                        justify-content: center;
                        align-items: center;
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        border-radius: 0.5rem;
                        padding: calc(1em - 1px);
                        background-color: #2e2f33}"""):
                    if f'{ath}_{f}_graph' in st.session_state:
                        st.plotly_chart(st.session_state[f'{ath}_{f}_graph'])
                st.write('')

elif st.session_state['generate_report']:
    for f in st.session_state['features_col']:
        with stylable_container(
            key=f'{f}container_title',
            css_styles="""
                {border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 0.5rem;
                padding: calc(1em - 1px);
                background-color: #2e2f33}"""):
            if f'{f}_graph' in st.session_state:
                st.plotly_chart(st.session_state[f'{f}_graph'])
        st.write('')

st.write('---')
if (st.session_state['generate_report']):
    data_download = st.session_state['data_download'].to_csv(index=False).encode('latin1')
    cdownload = st.columns([.8, .2])
    with cdownload[1]:
        with stylable_container(
            key='download_button', css_styles="""button {
                background-color: rgba(54,194,109,255); color: white;}
                """,): st.download_button(label=':inbox_tray: Download new file',
                                        data=data_download,
                                        file_name=f'data_trends.csv')