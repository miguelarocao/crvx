import datetime as dt
import os
import time

import gspread
import matplotlib
import pandas as pd
import pytz
import streamlit as st
from matplotlib import cm
from matplotlib.colors import ListedColormap

import plot, preprocess as pre
from google.oauth2.service_account import Credentials


# TODO: Add step about giving sheet access to README

@st.experimental_memo(ttl=60, show_spinner=True)
def get_sheets_data(cache_arg: int):
    """
    The cache arg is simply used to control when we hit the cache, so that we can manually trigger a new data pull
    by passing in a new cache_arg value.
    """

    gc = gspread.authorize(
        Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ],
        ))

    workbook = gc.open('Climbing Data Long')
    worksheet = workbook.worksheet('Indoor Bouldering Climbs')
    indoor_bouldering_data = worksheet.get('raw_climb_data')
    df_in = pre.header_to_col(pd.DataFrame(indoor_bouldering_data))

    worksheet = workbook.worksheet('Indoor Bouldering Sessions')
    indoor_bouldering_sessions = worksheet.get('raw_session_data')
    df_in_sess = pre.header_to_col(pd.DataFrame(indoor_bouldering_sessions))

    outdoor_bouldering_data = workbook.worksheet('Outdoor Bouldering').get()
    df_out = pre.header_to_col(pd.DataFrame(outdoor_bouldering_data))

    return {'indoor': df_in, 'indoor_sessions': df_in_sess, 'outdoor': df_out}, dt.datetime.now(dt.timezone.utc)


def main():
    # Sidebar
    colourmap = st.sidebar.selectbox('Colourmap', options=plot.SEQUENTIAL_CMAPS,
                                     index=plot.SEQUENTIAL_CMAPS.index('inferno'))

    # Title
    cmap = cm.get_cmap(colourmap, 5)  # Draw extra sample otherwise the "X" is too light on the white background
    st.markdown(f'<div style="font-family:sans-serif;font-size:300%;font-weight:bold">'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(0)[:3])}">C</span>'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(1)[:3])}">R</span>'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(2)[:3])}">V</span>'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(3)[:3])}">X</span>'
                f'</div>',
                unsafe_allow_html=True)
    st.write('_**C**limbing **R**ecord **V**isualisation e**X**perience_')

    st.warning('CRVX has moved to Streamlit Cloud. [Click here to be redirected](https://miguelarocao-crvx-srccrvx-a0kpvr.streamlitapp.com/).')

if __name__ == '__main__':
    main()
