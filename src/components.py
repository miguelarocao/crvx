import datetime
import streamlit as st


def add_date_filter(min_date: datetime.date, max_date: datetime.date):
    new_start_date = min_date
    new_end_date = max_date

    # Date selection
    date_filter = st.sidebar.radio(
        "Date filter",
        ('all', 'YTD', '1y', '6m', 'custom'))
    if date_filter == 'all':
        return new_start_date, new_end_date
    elif date_filter == 'YTD':
        new_start_date = max_date.replace(month=1, day=1)
    elif date_filter == '1y':
        new_start_date = max_date - datetime.timedelta(weeks=52)
    elif date_filter == '6m':
        new_start_date = max_date - datetime.timedelta(weeks=26)
    else:
        new_start_date = st.sidebar.date_input('Start date', min_date, min_value=min_date)
        new_end_date = st.sidebar.date_input('End date', max_date, max_value=max_date)

    if new_start_date >= new_end_date:
        st.error('Error: End date must fall after start date.')

    return new_start_date, new_end_date
