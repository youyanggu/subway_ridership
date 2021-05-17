import argparse
import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from constants import *

# Based on BART daily station exits: https://www.bart.gov/about/reports/ridership


def get_abbr_to_station_names():
    """Returns a dictionary of station abbreviations to names (e.g. EM -> Embarcadero)"""

    df_stations = pd.read_excel(
        'https://www.bart.gov/sites/default/files/docs/Station_Names.xls', dtype=str)
    abbr_to_station = df_stations.set_index('Two-Letter Station Code')['Station Name'].to_dict()
    return abbr_to_station


def get_daily_bart_ridership(start_date, end_date, out_fname=None):
    """Download BART daily exit data and parse it into a pandas dataframe"""

    url = 'http://64.111.127.166/DSE/Daily_Station_Exits.xlsx'
    print('============================')
    print('Downloading BART Daily Station Exits:', url)
    print('============================')
    df_bart = pd.read_excel(url)

    # Then combine and filter data
    df_bart['date'] = pd.to_datetime(df_bart['Date']).dt.date
    df_bart.columns = df_bart.columns.astype(str)
    df_bart = df_bart.dropna(axis=1, how='all')
    df_bart = df_bart.rename(columns={'Total' : 'exits'})
    df_bart = df_bart.loc[:, ~df_bart.columns.str.contains('^Unnamed')]

    print(f'Keeping data from {start_date} to {end_date}')
    df_bart_filt = df_bart[(df_bart['date'] >= start_date) & (df_bart['date'] <= end_date) & \
        (df_bart['exits'] > 0)]
    print('Last date of data:', df_bart_filt['date'].max())
    print('Num data points:', len(df_bart_filt))

    num_weeks = len(df_bart_filt) // 7
    df_bart_filt = df_bart_filt[-7*num_weeks:] # number of days is divisble by 7

    df_bart_daily = df_bart_filt.groupby('date')['exits'].sum().astype(int)
    df_bart_daily.name = 'exits_daily'
    if out_fname:
        print('Saving filtered output to:', out_fname)
        df_bart_daily.to_csv(out_fname)

    assert len(df_bart_daily) % 7 == 0, 'Num days must be a multiple of 7'
    return df_bart_daily, df_bart_filt


def print_busiest_bart_stations(df_bart_filt, abbr_to_station=None, save_stations=False):
    if abbr_to_station is None:
        abbr_to_station = get_abbr_to_station_names()
    df_bart_busiest = df_bart_filt[abbr_to_station.keys()].mean().sort_values(ascending=False)
    df_bart_busiest = pd.DataFrame(
        {'station_name': df_bart_busiest.index.map(abbr_to_station), 'exits_daily' : df_bart_busiest})
    df_bart_busiest.index.name = 'station_abbr'
    print('Top 10 busiest BART stations by avg daily exits:')
    print(df_bart_busiest.head(10))
    if save_stations:
        df_bart_busiest.to_csv('output_data/busiest_stations_bart.csv', float_format='%.0f')


def plot_bart_ridership(df_bart_daily, df_bart_filt, station_abbrs, abbr_to_station=None):
    if abbr_to_station is None:
        abbr_to_station = get_abbr_to_station_names()

    normal_ridership_bart = np.tile(df_bart_daily[:7].values, len(df_bart_daily) // 7)
    perc_normal_ridership_bart = df_bart_daily / normal_ridership_bart
    print('% normal ridership by date (BART):\n', perc_normal_ridership_bart)
    plt.plot(perc_normal_ridership_bart * 100, color=COLOR_BART, label='BART')

    for i, station_abbr in enumerate(station_abbrs):
        # e.g. Station abbreviations: https://www.bart.gov/sites/default/files/docs/Station_Names.xls
        assert station_abbr in abbr_to_station, f'No station found for abbreviation: {station_abbr}'
        station_name = abbr_to_station[station_abbr]
        print(f'Plotting station {station_abbr} / {station_name}...')
        color_idx = (i+2) % 10
        df_bart_station = df_bart_filt.groupby('date')[station_abbr].sum()
        assert len(df_bart_station) % 7 == 0, 'number of rows must be a multiple of 7'
        normal_ridership_bart_station = np.tile(df_bart_station[:7].values, len(df_bart_station) // 7)
        perc_normal_ridership_bart_station = df_bart_station / normal_ridership_bart_station
        plt.plot(perc_normal_ridership_bart_station * 100, color=f'C{color_idx}', label=station_name)

    if df_bart_daily.index.min() < LOCKDOWN_DATE_CA < df_bart_daily.index.max():
        plt.axvline(LOCKDOWN_DATE_CA, color=COLOR_BART_LOCKDOWN, ls='dashed',
            label='California Shelter-at-Home')

    ax = plt.gca()
    fig = plt.gcf()
    fig.autofmt_xdate()
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))

    plt.title('BART Ridership During COVID-19')
    plt.xlabel('Date')
    plt.ylabel('% of normal ridership')
    plt.legend()
    plt.grid()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=datetime.date.fromisoformat,
        default=datetime.date(2020,2,1),
        help=('approximate start date (default 2020-02-01). We use the week beginning at start_date to'
            ' be the baseline ridership.'))
    parser.add_argument('--end_date', type=datetime.date.fromisoformat,
        default=datetime.date.today(),
        help='approximate end date (default is today).')
    parser.add_argument('--out_fname',
        help='output csv file name to save parsed/filtered ridership data')
    parser.add_argument('--station_abbr', action='append',
        help=('additional BART station abbreviation to plot (e.g. EM for Embarcadero Station).'
            ' See station abbreviations: https://www.bart.gov/sites/default/files/docs/Station_Names.xls'))
    args = parser.parse_args()

    station_abbrs = args.station_abbr
    print('Station abbreviations:', station_abbrs)

    abbr_to_station = get_abbr_to_station_names()
    for abbr in station_abbrs:
        assert abbr in abbr_to_station, f'Unknown station abbrevation: {abbr}'

    df_bart_daily, df_bart_filt = get_daily_bart_ridership(args.start_date, args.end_date, args.out_fname)
    print_busiest_bart_stations(df_bart_filt, abbr_to_station)
    plot_bart_ridership(df_bart_daily, df_bart_filt, station_abbrs, abbr_to_station)
