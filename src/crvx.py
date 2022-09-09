import datetime as dt
import time

import gspread
import matplotlib
import pandas as pd
import pytz
import streamlit as st
from matplotlib import cm
from matplotlib.colors import ListedColormap

import plot, preprocess as pre
import components
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

    st.sidebar.markdown('---')
    cache_arg = 0
    if st.sidebar.button('Fetch data now!'):
        cache_arg = int(time.time())
    all_data, fetch_time = get_sheets_data(cache_arg)

    st.sidebar.write(f'_Last fetch @ '
                     f'{fetch_time.astimezone(pytz.timezone("Europe/London")).isoformat(timespec="seconds", sep=" ")}'
                     f' (1min cache)._')

    st.sidebar.markdown('---')

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

    # Initial processing
    all_data = pre.drop_nan_rows(all_data)
    all_data = pre.format_columns(all_data)
    err_msg = pre.validate_indoor_data(all_data['indoor'], all_data['indoor_sessions'])
    if err_msg:
        st.error(err_msg)
        st.stop()

    df_activity = pre.get_climbing_activity_df(all_data['indoor_sessions'], all_data['outdoor'])

    # Filter date (sidebar)
    start_date = df_activity['date'].min()
    filtered_start_date, filtered_end_date = components.add_date_filter(start_date, df_activity['date'].max())
    date_fmt="%Y/%m/%d"
    f'_Tracking Climbing from: {start_date.strftime(date_fmt)}. ' \
    f'Currently viewing: {filtered_start_date.strftime(date_fmt)} to {filtered_end_date.strftime(date_fmt)}_'

    df_activity = df_activity[(df_activity.index >= filtered_start_date.strftime('%Y-%m-%d')) &
                              (df_activity.index <= filtered_end_date.strftime('%Y-%m-%d'))]

    # Workout type filter (sidebar)
    st.sidebar.markdown('---')
    df_in = pd.merge(all_data['indoor'], df_activity, how='left', on='date')
    workout_types = list(df_activity['workout_type'].unique())
    selected_types = st.sidebar.multiselect(
        'Workout types',
        workout_types,
        workout_types)

    if not selected_types:
        st.error('No workout types selected :(')
        return

    df_in = df_in[df_in['workout_type'].isin(selected_types)]

    '## Climbing Activity'

    st.pyplot(plot.calendar_heat_map(df_activity, label='workout_type', colourmap=colourmap))

    '## Time-series visualisations'
    df_in = pre.distribute_climbs(df_in, random_seed=42)
    df_sent = df_in[df_in['sent']]  # drop unsent climbs

    # Aggregate sent climbs
    df_agg = df_sent.groupby(['date', 'v_grade']).agg({'sent': 'sum'}).reset_index().rename(
        columns={'sent': 'count'})

    # Add in missing grades
    df_agg = pre.expand_date_grades(df_agg)

    df_agg['count_csum'] = df_agg.groupby(['v_grade'])['count'].cumsum()
    df_agg['v_points'] = df_agg.apply(pre.apply_v_grade_multiplier, axis=1, args=('count',))  # noqa
    df_agg['v_points_csum'] = df_agg.apply(pre.apply_v_grade_multiplier, axis=1, args=('count_csum',))  # noqa

    show_bar_labels = st.checkbox('Show bar chart labels', value=False)

    st.altair_chart(plot.cumulative_stacked_area_chart(df_agg, "count_csum:Q", colourmap,
                                                       title='Total climb count'),
                    use_container_width=True)

    st.altair_chart(
        plot.stacked_bar_chart(df_agg, 'count:Q', colourmap, title='Climb Count', show_labels=show_bar_labels),
        use_container_width=True)

    st.altair_chart(plot.cumulative_stacked_area_chart(df_agg, "v_points_csum:Q", colourmap,
                                                       title='Total V-point'),
                    use_container_width=True)

    st.altair_chart(
        plot.stacked_bar_chart(df_agg, 'v_points:Q', colourmap, title='V Points', show_labels=show_bar_labels),
        use_container_width=True)

    '## Grade Total Visualisations'
    draw_targets = st.checkbox('Enable "grade pyramid" target bars (grey).', value=True)
    total_v_grades = df_sent.groupby('v_grade').agg(total_count=('sent', 'sum')).reset_index()
    total_v_grades['target_count'] = pre.get_pyramid_targets(total_v_grades['total_count'])
    st.altair_chart(
        plot.total_v_grade_horizontal_bar_char(total_v_grades, colourmap, draw_targets=draw_targets).properties(
            width=550,
            height=350),
        use_container_width=True)

    df_sent_with_type = df_sent.merge(all_data['indoor_sessions'][['date', 'workout_type']],
                                      how='left', on='date', validate='many_to_one')
    st.altair_chart(plot.workout_type_v_grade_bar_charts(df_sent_with_type, colourmap).properties(
        width=175,
        height=250),
        use_container_width=False)

    '## Attempt Visualisations'

    df_att = df_in.copy()
    df_att['attempts'] = df_att['attempts'].fillna(1).astype(int)
    df_att = pre.expand_attempts(df_att)
    df_att = df_att.groupby(['v_grade', 'attempt_num', 'sent']).agg(count=('date', 'count')).reset_index()
    df_att['sent_str'] = df_att['sent'].astype(str)
    st.altair_chart(plot.get_attempt_bar_chart(df_att, colourmap), use_container_width=True)

    df_sent = df_att[df_att['sent']].copy()

    st.altair_chart(plot.get_send_attempt_normalized(df_sent, colourmap), use_container_width=True)

    if st.checkbox('Hide flashes', value=True):
        df_att = df_att[(df_att['attempt_num'] > 1) | (~df_att['sent'])]

    st.altair_chart(plot.get_attempt_and_send_bubble_chart(df_att, colourmap), use_container_width=True)

    st.sidebar.markdown('---')
    st.sidebar.markdown('[_GitHub Source_](https://github.com/miguelarocao/crvx)')

if __name__ == '__main__':
    main()
