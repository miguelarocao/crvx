import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt
import calmap
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import plot
import matplotlib

# constants
MAX_VGRADE = 11
VGRADE_COLS = ['VB', 'VB-0', 'V0', 'V1', 'V1-2', 'V2', 'V3', 'V3-4', 'V4', 'V5', 'V5-6', 'V6', 'V7', 'V8', 'V9', 'V10']
VGRADE_NUM_COLS = [f'V{grade}' for grade in range(MAX_VGRADE)]
V_GRADE_MULT = {f'V{grade}': grade for grade in range(MAX_VGRADE)}
V_GRADE_MULT['V0'] = 0.5




def header_to_col(df):
    df.columns = df.iloc[0]
    return df.iloc[1:]


# TODO: We'll need to make this cache properly later
def get_sheets_data():
    gc = gspread.service_account(filename='credentials.json')

    workbook = gc.open('Climbing Data')
    worksheet = workbook.worksheet('Indoor Bouldering')
    indoor_bouldering_data = worksheet.get('raw_data')  # named range
    df_in = header_to_col(pd.DataFrame(indoor_bouldering_data))

    outdoor_bouldering_data = workbook.worksheet('Outdoor Bouldering').get()
    df_out = header_to_col(pd.DataFrame(outdoor_bouldering_data))

    return {'indoor': df_in, 'outdoor': df_out}


def distribute_split_grades(df):
    to_drop = []
    for col in VGRADE_COLS:
        if '-' in col:
            lower_grade, upper_grade = col[1:].split('-')
            df[f'V{lower_grade}'] += df[col] / 2
            df[f'V{upper_grade}'] += df[col] / 2
            to_drop.append(col)
    return df.drop(columns=to_drop)


def get_df_grades(df):
    df_grades = df[['Date'] + VGRADE_COLS] #.set_index('Date').rename_axis('v_grade', axis=1)
    df_grades = df_grades.set_index('Date').replace('', 0)
    df_grades = df_grades.astype({v: int for v in VGRADE_COLS})
    df_grades = distribute_split_grades(df_grades)
    df_grades = df_grades.drop(columns=['VB'])

    col_mask = df_grades[VGRADE_NUM_COLS].sum() > 0

    df_grades = df_grades.loc[:, col_mask]
    df_grades.reset_index(inplace=True)
    df_grades['Date'] = pd.to_datetime(df_grades['Date'], format='%d/%m/%Y')
    return df_grades


def get_long_format(df_grades, v_cols):
    df_grades_long = pd.melt(df_grades.copy(), value_vars=v_cols, id_vars=['Date'], value_name='count',
                             var_name='v_grade')
    return df_grades_long


def main():

    # Title
    st.write('# CRVX')
    st.write(' *__C__limbing **R**ecord **V**isualisation e**X**perience* ')
    all_data = get_sheets_data()

    colourmap = st.selectbox('Colourmap', options=plot.SEQUENTIAL_CMAPS, index=plot.SEQUENTIAL_CMAPS.index('plasma'))

    df_dates = all_data['indoor'][['Date', 'workout type']]
    df_dates = df_dates.rename(columns={'workout type': 'workout_type'})
    outdoor_df = pd.DataFrame(
        {'Date': all_data['outdoor']['Date'].unique(),
         'workout_type': ['outdoors'] * all_data['outdoor']['Date'].nunique()})
    df_dates = pd.concat([df_dates, outdoor_df])
    df_dates['workout_int'] = df_dates['workout_type'].astype('category')
    df_dates = df_dates.set_index(pd.to_datetime(df_dates['Date'], format='%d/%m/%Y'))

    # TODO: Most recent session

    '## Climbing Activity'
    f'_Tracking Climbing from: {df_dates["Date"].min()}_'

    st.pyplot(plot.calendar_heat_map(df_dates, label='workout_int', colourmap=colourmap),
              use_container_width=True)
    '## Time-series visualisations'

    df_grades = get_df_grades(all_data['indoor'])
    remaining_v_cols = df_grades.drop(columns='Date').columns.values

    df_grades_long = get_long_format(df_grades, remaining_v_cols)
    df_grades_long['count_csum'] = df_grades_long.groupby(['v_grade'])['count'].cumsum()
    df_grades_long['v_grade'] = df_grades_long['v_grade'].str[1:]

    st.altair_chart(plot.cumulative_count_sum_chart(df_grades_long, "count_csum:Q", colourmap,
                                                    title='Count of climbs by grade'),
                    use_container_width=True)

    def apply_v_grade_multipler(row, target_col):
        return V_GRADE_MULT[f'V{row["v_grade"]}'] * row[target_col]

    df_grades_long['v_points'] = df_grades_long.apply(apply_v_grade_multipler, axis=1, args=('count',)) # noqa
    df_grades_long['v_points_csum'] = df_grades_long.apply(apply_v_grade_multipler, axis=1, args=('count_csum',)) # noqa

    st.altair_chart(plot.cumulative_count_sum_chart(df_grades_long, "v_points_csum:Q", colourmap,
                                                    title='Count of V-points by grade'),
                    use_container_width=True)

    total_v_grades = pd.DataFrame(df_grades.set_index('Date').sum(),
                                  columns=['total_count']).rename_axis('v_grade').reset_index()

    # TODO: Bar charts for per session
    # TODO: Strength days
    # TODO: Volume days


    # TODO: Move to own functions
    # Populate targets
    total_v_grades['target_count'] = total_v_grades['total_count'].copy()
    for i, row in total_v_grades[::-1].iterrows():
        if i == len(total_v_grades) - 1:
            continue
        total_v_grades.loc[i, 'target_count'] = max(total_v_grades.loc[i + 1, 'target_count'] * 2, row['target_count'])

    # Target V-Grade Plot
    bars = alt.Chart(total_v_grades).mark_bar().encode(
        x=alt.Y('total_count:Q', title='Climb Count'),
        y=alt.Y('v_grade:O', sort=remaining_v_cols[::-1], title='V Grade'),
        color=alt.Color('v_grade:O', scale=alt.Scale(scheme=colourmap)),
    )

    text = bars.mark_text(
        align='left',
        baseline='middle',
        dx=3  # Nudges text to right so it doesn't appear on top of the bar
    ).encode(
        text='total_count:Q'
    )

    bars_target = alt.Chart(total_v_grades).mark_bar(opacity=0.25).encode(
        x='target_count:Q',
        y=alt.Y('v_grade:O', sort=remaining_v_cols[::-1]),
    )

    chart = (bars + text + bars_target).properties(width=600, height=400)
    st.altair_chart(chart, use_container_width=True)

main()
