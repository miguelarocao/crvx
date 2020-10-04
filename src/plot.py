import altair as alt
import pandas as pd
import calmap
import numpy as np
from matplotlib import cm
from mpl_toolkits.axes_grid1 import make_axes_locatable

SEQUENTIAL_CMAPS = [
    # 'blues',
    # 'tealblues',
    # 'teals',
    # 'greens',
    # 'browns',
    # 'oranges',
    # 'reds',
    # 'purples',
    # 'warmgreys',
    # 'greys', # TODO: Re-enable Vega colormaps with Matplotlib equivalent
    'viridis',
    'magma',
    'inferno',
    'plasma',
    # 'bluegreen',
    # 'bluepurpl',
    # 'oldgreen',
    # 'oldorange',
    # 'goldred',
    # 'greenblue',
    # 'orangered',
    # 'purplebluegreen',
    # 'purpleblue',
    # 'purplered',
    # 'redpurple',
    # 'yellowgreenblue',
    # 'yellowgreen',
    # 'yelloworangebrown',
    # 'yelloworangered',
    # 'darkblue',
    # 'darkgold',
    # 'darkgreen',
    # 'darkmulti',
    # 'darkred',
    # 'lightgreyred',
    # 'lightgreyteal',
    # 'lightmulti',
    # 'lightorange',
    # 'lighttealblue'
]

LABEL_FONT_SIZE = 10
TITLE_FONT_SIZE = 13


def calendar_heat_map(df_dates, label: str, colourmap: str):
    assert (df_dates[label] != 0).all()
    num_labels = df_dates[label].nunique()
    cmap = cm.get_cmap(colourmap, num_labels)
    fig, ax = calmap.calendarplot(df_dates[label].cat.codes,
                                  daylabels='MTWTFSS',
                                  dayticks=[0, 2, 4, 6], cmap=cmap,
                                  fillcolor='lightgrey', linewidth=1.0,
                                  fig_kws=dict(figsize=(8, 4)),
                                  how=None)  # noqa
    cax = ax[0]
    divider = make_axes_locatable(cax)
    lcax = divider.append_axes("right", size="2%", pad=0.5)
    cb = fig.colorbar(cax.get_children()[1], cax=lcax)
    cb.set_ticks((np.arange(num_labels) + 0.5) * (num_labels - 1) / num_labels)
    cb.set_ticklabels(df_dates[label].cat.categories.values)

    return fig


def cumulative_stacked_area_chart(df_long: pd.DataFrame, y: str, colourmap: str, title: str):
    return alt.Chart(df_long).mark_area().encode(
        x='date:T',
        y=alt.Y(y, title=title),
        color=alt.Color('v_grade:O', scale=alt.Scale(scheme=colourmap), title='V Grade'),
        order=alt.Order('v_grade:O', sort='ascending')
    ).configure_axis(
        labelFontSize=LABEL_FONT_SIZE,
        titleFontSize=TITLE_FONT_SIZE
    )


def stacked_bar_chart(df_long: pd.DataFrame, y: str, colourmap: str, title: str):
    bars = alt.Chart(df_long).mark_bar().encode(
        x=alt.X('date:O', title='Date'),
        y=alt.Y(y, title=title),
        color=alt.Color('v_grade:O', scale=alt.Scale(scheme=colourmap), title='V Grade'),
        order=alt.Order('v_grade:O', sort='ascending'))

    text = alt.Chart(df_long).mark_text(dy=-7).encode(
        x=alt.X('yearmonthdate(date):O', title='Date'),
        y=alt.Y(f'sum({y.split(":")[0]}):Q', stack='zero'),
        text=f'sum({y.split(":")[0]}):Q')

    return (bars + text).configure_axis(
        labelFontSize=LABEL_FONT_SIZE,
        titleFontSize=TITLE_FONT_SIZE
    )


def total_v_grade_horizontal_bar_char(total_v_grades, colourmap, draw_targets=False):
    assert not draw_targets or 'target_count' in total_v_grades.columns, "Cannot draw targets that don't exist!"

    v_grade_ints = sorted(total_v_grades['v_grade'], reverse=True)
    bars = alt.Chart(total_v_grades).mark_bar().encode(
        x=alt.X('total_count:Q', title='Climb Count'),
        y=alt.Y('v_grade:O', sort=v_grade_ints, title='V Grade'),
        color=alt.Color('v_grade:O', scale=alt.Scale(scheme=colourmap), title='V Grade'),
    )

    text = bars.mark_text(
        align='left',
        baseline='middle',
        dx=3  # Nudges text to right so it doesn't appear on top of the bar
    ).encode(
        text='total_count:Q'
    )

    output = bars + text
    if draw_targets:
        bars_target = alt.Chart(total_v_grades).mark_bar(opacity=0.25).encode(
            x='target_count:Q',
            y=alt.Y('v_grade:O', sort=v_grade_ints),
        )
        output += bars_target

    return output.configure_axis(
        labelFontSize=LABEL_FONT_SIZE,
        titleFontSize=TITLE_FONT_SIZE
    )


def workout_type_v_grade_bar_charts(df, colourmap):
    v_grade_ints =sorted(df['v_grade'].unique(), reverse=True)
    bars = alt.Chart(df).mark_bar().encode(
        x=alt.Y('sum(sent):Q', title='Climb Count'),
        y=alt.Y('v_grade:O', sort=v_grade_ints, title='V Grade'),
        color=alt.Color('v_grade:O', scale=alt.Scale(scheme=colourmap), title='V Grade'),
        column=alt.Column('workout_type:N', title='By Workout Type', sort='descending',
                          header=alt.Header(titleFontSize=12, labelFontSize=12))
    ).configure_axis(
        labelFontSize=LABEL_FONT_SIZE,
        titleFontSize=TITLE_FONT_SIZE
    )
    return bars
