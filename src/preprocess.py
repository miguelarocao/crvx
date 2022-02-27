import pandas as pd
import random
import streamlit as st
from typing import Optional
from copy import deepcopy
from typing import Dict
from constants import V_GRADE_MULT


def header_to_col(df):
    df.columns = df.iloc[0]
    return df.iloc[1:]


def drop_nan_rows(all_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    output = {}
    for name, df in all_data.items():
        output[name] = df.dropna(axis=0)
        num_na = len(df) - len(output[name])
        if num_na:
            st.warning(f'Dropped {len(df) - len(output[name])} rows with NaNs from dataframe {name}...')
    return output


def format_columns(all_data: Dict) -> Dict:
    out = deepcopy(all_data)
    # Rename
    out['indoor'] = out['indoor'].rename(columns={'Date': 'date',
                                                  'V Grade': 'v_grade',
                                                  'Count Multiplier': 'count_multiplier',
                                                  'Attempts (w/ send)': 'attempts',
                                                  'Sent': 'sent'})
    out['indoor_sessions'] = out['indoor_sessions'].rename(columns={'Date': 'date',
                                                                    'workout type': 'workout_type',
                                                                    'climbing time': 'climbing_time',
                                                                    'total time': 'total_time'})
    out['outdoor'] = out['outdoor'].rename(columns={'Date': 'date',
                                                    'Grade': 'v_grade'})

    def _format_date_col(date_col):
        return pd.to_datetime(date_col, format='%d/%m/%Y')

    # Remove "V"
    out['indoor']['v_grade'] = out['indoor']['v_grade'].str[1:]

    # apply types
    out['indoor']['date'] = _format_date_col(out['indoor']['date'])
    numeric_cols = ['count_multiplier', 'attempts']
    out['indoor'][numeric_cols] = out['indoor'][numeric_cols].apply(pd.to_numeric)
    out['indoor']['sent'] = out['indoor']['sent'].apply(lambda x: x == 'TRUE')

    out['indoor_sessions']['date'] = _format_date_col(out['indoor_sessions']['date'])

    out['outdoor']['date'] = _format_date_col(out['outdoor']['date'])

    return out


def validate_indoor_data(df_in: pd.DataFrame, df_in_sess: pd.DataFrame) -> Optional[str]:
    climb_dates = set(df_in['date'])
    sess_dates = set(df_in_sess['date'])

    if climb_dates - sess_dates:
        return f'Indoor climbing data contains dates not in sessions: {climb_dates - sess_dates}'
    if sess_dates - climb_dates:
        return f'Indoor climbing data is missing dates found in sessions: {sess_dates - climb_dates}'

    if df_in_sess['date'].nunique() != len(df_in_sess):
        return f'Indoor climbing sessions contains multiple entries for a date!'

    return None


def get_climbing_activity_df(df_in_sess: pd.DataFrame, df_out: pd.DataFrame) -> pd.DataFrame:
    df_dates = df_in_sess[['date', 'workout_type']]
    outdoor_df = pd.DataFrame(
        {'date': df_out['date'].unique(),
         'workout_type': ['outdoors'] * df_out['date'].nunique()})
    df_dates = pd.concat([df_dates, outdoor_df])
    df_dates['workout_type'] = df_dates['workout_type'].astype('category')
    return df_dates.set_index(pd.to_datetime(df_dates['date'], format='%d/%m/%Y')).rename_axis(None)


def _split_grade(v_grade):
    if '-' in v_grade:
        lower_grade, upper_grade = v_grade.split('-')
        return f'{random.choice([lower_grade, upper_grade])}'
    else:
        return v_grade


def distribute_climbs(df_in: pd.DataFrame, random_seed: int, drop_vb=True) -> pd.DataFrame:
    """ Distributes climbs based on the count multiplier and resolves split grades into integers."""
    # Apply count multiplier
    expected_num_climb = df_in['count_multiplier'].sum()
    df_in = df_in.reindex(df_in.index.repeat(df_in['count_multiplier'])).reset_index(drop=True)
    df_in = df_in.drop(columns='count_multiplier')
    assert len(df_in) == expected_num_climb

    random.seed(random_seed)
    df_in['v_grade'] = df_in['v_grade'].apply(_split_grade)

    if drop_vb:
        df_in = df_in[df_in['v_grade'] != 'B']
        df_in['v_grade'] = df_in['v_grade'].astype(int)

    return df_in


def expand_date_grades(df: pd.DataFrame) -> pd.DataFrame:
    """ Expands each date to include each v-grade. """
    unique_dates = sorted(df['date'].unique())
    unique_v_grades = sorted(df['v_grade'].unique())
    expand_df = pd.DataFrame(index=pd.MultiIndex.from_product([unique_dates, unique_v_grades],
                                                              names=['date', 'v_grade'])).reset_index()
    df = expand_df.merge(df, on=['date', 'v_grade'], how='left', validate='one_to_many')
    df['count'] = df['count'].fillna(0)

    return df.sort_values(by=['date', 'v_grade'])


def expand_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """ Converts number of attempts, to individual attempts."""

    output = []
    for _, row in df.iterrows():
        sent = row['sent']
        for i in range(1, row['attempts'] + 1):
            row['attempt_num'] = i
            row['sent'] = sent if i == row['attempts'] else False
            output.append(pd.DataFrame([row]))

    return pd.concat(output)


def apply_v_grade_multiplier(row, target_col):
    return V_GRADE_MULT[f'V{row["v_grade"]}'] * row[target_col]


def get_pyramid_targets(total_v_count):
    targets = total_v_count.copy()
    for i, count in targets[::-1].iteritems():
        if i == len(targets) - 1:
            continue
        targets[i] = max(targets[i + 1] * 2, count)
    return targets


# Currently unused
def get_perc_sent_by_grade(df):
    df_att_total = df.groupby(['v_grade', 'attempt_num']).agg(total_count=('count', 'sum')).reset_index()
    df_att_norm = df.merge(df_att_total, on=['v_grade', 'attempt_num'], how='left', validate='many_to_one')
    df_att_norm['perc_sent'] = df_att_norm['count'] / df_att_norm['total_count']
    df = df_att_norm[df_att_norm['sent']]
    return df
