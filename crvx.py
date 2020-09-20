import streamlit as st
import gspread
import pandas as pd
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import plot
import matplotlib
from matplotlib import cm
import os

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
    gc = gspread.service_account(filename=os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))

    workbook = gc.open('Climbing Data')
    worksheet = workbook.worksheet('Indoor Bouldering')
    indoor_bouldering_data = worksheet.get('raw_data')  # named range
    df_in = header_to_col(pd.DataFrame(indoor_bouldering_data))

    outdoor_bouldering_data = workbook.worksheet('Outdoor Bouldering').get()
    df_out = header_to_col(pd.DataFrame(outdoor_bouldering_data))

    return {'indoor': df_in, 'outdoor': df_out}


# TODO: Refactor to make more obvious this is happening
def distribute_split_grades(df):
    to_drop = []
    for col in VGRADE_COLS:
        if '-' in col:
            lower_grade, upper_grade = col[1:].split('-')
            df[f'V{lower_grade}'] += (df[col] + 1) // 2  # If odd we give the "split" climb to the lower one
            df[f'V{upper_grade}'] += df[col] // 2
            to_drop.append(col)
    return df.drop(columns=to_drop)


def get_df_grades(df):
    df_grades = df[VGRADE_COLS].replace('', 0)
    df_grades = df_grades.astype({v: int for v in VGRADE_COLS})
    df_grades = distribute_split_grades(df_grades)
    df_grades = df_grades.drop(columns=['VB'])

    col_mask = df_grades[VGRADE_NUM_COLS].sum() > 0
    df_grades = df_grades.loc[:, col_mask]

    df_grades['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    df_grades['workout_type'] = df['workout type']
    return df_grades


def get_df_dates(df_in, df_out):
    df_dates = df_in[['Date', 'workout type']]
    df_dates = df_dates.rename(columns={'workout type': 'workout_type'})
    outdoor_df = pd.DataFrame(
        {'Date': df_out['Date'].unique(),
         'workout_type': ['outdoors'] * df_out['Date'].nunique()})
    df_dates = pd.concat([df_dates, outdoor_df])
    df_dates['workout_type'] = df_dates['workout_type'].astype('category')
    return df_dates.set_index(pd.to_datetime(df_dates['Date'], format='%d/%m/%Y'))


def get_long_format(df_grades, v_cols):
    df_grades_long = pd.melt(df_grades.copy(), value_vars=v_cols, id_vars=['Date', 'workout_type'], value_name='count',
                             var_name='v_grade')
    # TODO: Add some checks that format is as expected. 1 row per (date, v_grade)
    return df_grades_long


def get_pyramid_targets(total_v_count):
    targets = total_v_count.copy()
    for i, count in targets[::-1].iteritems():
        if i == len(targets) - 1:
            continue
        targets[i] = max(targets[i + 1] * 2, count)
    return targets


def main():
    colourmap = st.sidebar.selectbox('Colourmap', options=plot.SEQUENTIAL_CMAPS,
                                     index=plot.SEQUENTIAL_CMAPS.index('plasma'))

    # Title
    cmap = cm.get_cmap(colourmap, 5)  # Draw extra sample otherwise the "X" is too light on the white background
    st.markdown(f'<div style="font-family:sans-serif;font-size:300%;font-weight:bold">'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(0)[:3])}">C</span>'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(1)[:3])}">R</span>'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(2)[:3])}">V</span>'
                f'<span style="color:{matplotlib.colors.rgb2hex(cmap(3)[:3])}">X</span>'
                f'</div>',
                unsafe_allow_html=True)
    st.write(' *__C__limbing **R**ecord **V**isualisation e**X**perience* ')
    all_data = get_sheets_data()

    df_dates = get_df_dates(all_data['indoor'], all_data['outdoor'])

    # TODO: Most recent session

    '## Climbing Activity'
    f'_Tracking Climbing from: {df_dates["Date"].min()}_'

    st.pyplot(plot.calendar_heat_map(df_dates, label='workout_type', colourmap=colourmap))

    '## Time-series visualisations'
    df_grades = get_df_grades(all_data['indoor'])
    remaining_v_cols = df_grades.drop(columns=['Date', 'workout_type']).columns.values

    df_grades_long = get_long_format(df_grades, remaining_v_cols)
    df_grades_long['count_csum'] = df_grades_long.groupby(['v_grade'])['count'].cumsum()
    df_grades_long['v_grade'] = df_grades_long['v_grade'].str[1:]

    def _apply_v_grade_multiplier(row, target_col):
        return V_GRADE_MULT[f'V{row["v_grade"]}'] * row[target_col]

    df_grades_long['v_points'] = df_grades_long.apply(_apply_v_grade_multiplier, axis=1, args=('count',))  # noqa
    df_grades_long['v_points_csum'] = df_grades_long.apply(_apply_v_grade_multiplier, axis=1,  # noqa
                                                           args=('count_csum',))

    st.altair_chart(plot.cumulative_stacked_area_chart(df_grades_long, "count_csum:Q", colourmap,
                                                       title='Total climb count'),
                    use_container_width=True)

    st.altair_chart(plot.stacked_bar_chart(df_grades_long, 'count:Q', colourmap, title='Climb Count'),
                    use_container_width=True)

    st.altair_chart(plot.cumulative_stacked_area_chart(df_grades_long, "v_points_csum:Q", colourmap,
                                                       title='Total V-point'),
                    use_container_width=True)

    st.altair_chart(plot.stacked_bar_chart(df_grades_long, 'v_points:Q', colourmap, title='V Points'),
                    use_container_width=True)

    # TODO: Add climbing time viz

    '## Grade Total Visualisations'
    draw_targets = st.checkbox('Enable "grade pyramid" target bars (grey).', value=True)
    total_v_grades = df_grades_long.groupby('v_grade').agg(total_count=('count', 'sum')).reset_index()
    total_v_grades['target_count'] = get_pyramid_targets(total_v_grades['total_count'])
    st.altair_chart(
        plot.total_v_grade_horizontal_bar_char(total_v_grades, colourmap, draw_targets=draw_targets).properties(
            width=550,
            height=350),
        use_container_width=True)

    st.altair_chart(plot.workout_type_v_grade_bar_charts(df_grades_long, colourmap).properties(width=275,
                                                                                               height=250))


main()
