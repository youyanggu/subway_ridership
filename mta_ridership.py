import argparse
import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from constants import *

# Based on MTA turnstile data: http://web.mta.info/developers/turnstile.html


pd.plotting.register_matplotlib_converters()
pd.options.mode.chained_assignment = None

def text_to_df(text):
    # converts text to a pandas dataframe
    lines = text.split('\n')
    cols = [c.strip() for c in lines[0].split(',')]
    lines_arr = []
    for line in lines[1:]:
        if line:
            line = line.split(',')
            assert len(line) == len(cols)
            lines_arr.append([l.strip() for l in line])
    df = pd.DataFrame(lines_arr, columns=cols)
    return df


def get_last_saturday(date):
    shift = (date.weekday() + 2) % 7
    last_sat = date - datetime.timedelta(days=shift)

    return last_sat


def get_daily_mta_ridership(start_date, end_date, out_fname=None):
    """Download MTA daily turnstile entries and parse it into a pandas dataframe"""
    print('============================')
    print(f'Downloading MTA data from {start_date} to {end_date}')
    print('============================')

    sort_cols = ['C/A', 'UNIT', 'SCP', 'STATION', 'LINENAME', 'DIVISION', 'date']
    last_sat = get_last_saturday(start_date)
    date = last_sat
    dfs = []
    while date <= end_date + datetime.timedelta(days=7):
        url = 'http://web.mta.info/developers/data/nyct/turnstile/turnstile_{}.txt'.format(
            date.strftime('%y%m%d'))
        print('Downloading:', url)
        resp = requests.get(url)
        print(resp)

        data = resp.text
        df_week = text_to_df(data)

        print('Filtering data...')
        df_week['date'] = pd.to_datetime(df_week['DATE']).dt.date

        df_week = df_week.sort_values(sort_cols).reset_index(drop=True)
        df_daily = df_week.drop_duplicates(sort_cols, keep='last').reset_index(drop=True)

        print(f'Filtered from {len(df_week):,} rows to {len(df_daily):,} rows')
        dfs.append(df_daily)
        date += datetime.timedelta(days=7) 

    print('Combining data...')
    df_all = pd.concat(dfs)
    df_all = df_all.sort_values(sort_cols).reset_index(drop=True)
    df_all['ENTRIES'] = df_all['ENTRIES'].astype(int)
    df_all['EXITS'] = df_all['EXITS'].astype(int)
    df_all['entries_daily'] = df_all.groupby(sort_cols[:-1])['ENTRIES'].diff()
    df_all['exits_daily'] = df_all.groupby(sort_cols[:-1])['EXITS'].diff()

    df_mta_filt = df_all[(df_all['entries_daily'] >= 0) & (df_all['entries_daily'] < 20000) & \
        (df_all['exits_daily'] >= 0) & (df_all['exits_daily'] < 20000)]

    assert df_mta_filt['date'].min() <= start_date, \
        f"Missing dates: {df_mta_filt['date'].min()} > {start_date}"
    df_mta_filt = df_mta_filt[df_mta_filt['date'] >= start_date]

    df_mta_daily = df_mta_filt.groupby('date')['entries_daily'].sum().astype(int)
    if out_fname:
        print('Saving filtered output to:', out_fname)
        df_mta_daily.to_csv(out_fname)

    assert len(df_mta_daily) % 7 == 0, 'number of rows must be a multiple of 7'
    return df_mta_daily, df_mta_filt


def print_busiest_mta_stations(df_mta_filt, save_stations=False):
    df_mta_busiest = df_mta_filt.groupby(['STATION', 'date'])['entries_daily'].sum().mean(
        level=0).sort_values(ascending=False)
    df_mta_busiest.name = 'average_entries_per_turnstile'
    print('Top 10 busiest MTA stations by avg daily entries:')
    print(df_mta_busiest.head(10))
    if save_stations:
        df_mta_busiest.to_csv('output_data/busiest_stations_mta.csv', float_format='%.0f')


def plot_mta_ridership(df_mta_daily, df_mta_filt, station_names=[]):
    normal_ridership_mta = np.tile(df_mta_daily[:7].values, len(df_mta_daily) // 7)
    perc_normal_ridership_mta = df_mta_daily / normal_ridership_mta
    print('% normal ridership by date (MTA):\n', perc_normal_ridership_mta)
    plt.plot(perc_normal_ridership_mta * 100, color=COLOR_MTA, label='MTA')

    for i, station_name in enumerate(station_names):
        # e.g. 34 St-Herald Sq, Grd Cntrl-42 St
        print('Plotting station name:', station_name)
        color_idx = (i+2) % 10
        df_mta_station = df_mta_filt[
            df_mta_filt['STATION'] == station_name.upper()].groupby('date')['entries_daily'].sum()
        if len(df_mta_station) == 0:
            print('No station found for name:', station_name)
        else:
            assert len(df_mta_station) % 7 == 0, 'number of rows must be a multiple of 7'
            normal_ridership_mta_station = np.tile(df_mta_station[:7].values, len(df_mta_station) // 7)
            perc_normal_ridership_mta_station = df_mta_station / normal_ridership_mta_station
            plt.plot(perc_normal_ridership_mta_station * 100, color=f'C{color_idx}', label=station_name)

    if df_mta_daily.index.min() < LOCKDOWN_DATE_NY < df_mta_daily.index.max():
        plt.axvline(LOCKDOWN_DATE_NY, color=COLOR_MTA_LOCKDOWN, ls='dashed',
            label='New York Shelter-at-Home')

    ax = plt.gca()
    fig = plt.gcf()
    fig.autofmt_xdate()
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))

    plt.title('NYC MTA Ridership During COVID-19')
    plt.xlabel('Date')
    plt.ylabel('% of normal ridership')
    plt.legend()
    plt.grid()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=datetime.date.fromisoformat,
        default=datetime.date(2020,2,1),
        help=('approximate start date (default 2020-02-01). We use the week beginning at start_date'
            ' to be the baseline ridership. Note: must be a Saturday'))
    parser.add_argument('--end_date', type=datetime.date.fromisoformat,
        default=datetime.date.today(),
        help='approximate end date (default is today).')
    parser.add_argument('--out_fname',
        help='output csv file name to save parsed/filtered ridership data')
    parser.add_argument('--station_name', action='append', nargs='+',
        help=('additional MTA station names to plot (case-insensitive).'
            ' For station names, see mta_busiest_stations.csv'))
    args = parser.parse_args()

    station_names = None
    if args.station_name:
        station_names = [' '.join(station_name) for station_name in args.station_name]
    print('Station names:', station_names)

    df_mta_daily, df_mta_filt = get_daily_mta_ridership(args.start_date, args.end_date, args.out_fname)
    print_busiest_mta_stations(df_mta_filt)
    plot_mta_ridership(df_mta_daily, df_mta_filt, station_names)
