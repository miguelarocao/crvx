import altair as alt
import pandas as pd
import calmap
import numpy as np
from matplotlib import cm
from mpl_toolkits.axes_grid1 import make_axes_locatable

SEQUENTIAL_CMAPS = [
    'blues',
    'tealblues',
    'teals',
    'greens',
    'browns',
    'oranges',
    'reds',
    'purples',
    'warmgreys',
    'greys',
    'viridis',
    'magma',
    'inferno',
    'plasma',
    'bluegreen',
    'bluepurpl',
    'oldgreen',
    'oldorange',
    'goldred',
    'greenblue',
    'orangered',
    'purplebluegreen',
    'purpleblue',
    'purplered',
    'redpurple',
    'yellowgreenblue',
    'yellowgreen',
    'yelloworangebrown',
    'yelloworangered',
    'darkblue',
    'darkgold',
    'darkgreen',
    'darkmulti',
    'darkred',
    'lightgreyred',
    'lightgreyteal',
    'lightmulti',
    'lightorange',
    'lighttealblue']


def calendar_heat_map(df_dates, label: str, colourmap: str):
    cmap = cm.get_cmap(colourmap, 3)
    fig, ax = calmap.calendarplot(df_dates['workout_int'].cat.codes,
                                  daylabels='MTWTFSS',
                                  dayticks=[0, 2, 4, 6], cmap=cmap,
                                  fillcolor='lightgrey', linewidth=1.0,
                                  fig_kws=dict(figsize=(8, 4)),
                                  how=None)  # noqa
    cax = ax[0]
    divider = make_axes_locatable(cax)
    lcax = divider.append_axes("right", size="2%", pad=0.5)
    cb = fig.colorbar(cax.get_children()[1], cax=lcax)
    num_labels = df_dates[label].nunique()
    cb.set_ticks((np.arange(num_labels) + 0.5) * (num_labels - 1) / num_labels)
    cb.set_ticklabels(df_dates[label].cat.categories.values)

    return fig


def cumulative_count_sum_chart(df_long: pd.DataFrame, y: str, colourmap: str, title: str):
    return alt.Chart(df_long).mark_area().encode(
        x='Date:T',
        y=alt.Y(y, title=title),
        color=alt.Color('v_grade:O', scale=alt.Scale(scheme=colourmap), title='V Grade'),
        order=alt.Order('v_grade:O', sort='ascending')
    ).configure_axis(
        labelFontSize=10,
        titleFontSize=12
    )
