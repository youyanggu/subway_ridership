import argparse
import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Based on BART daily station exits: https://www.bart.gov/about/reports/ridership

def get_daily_bart_ridership(start_date, out_fname=None):
    """Download BART data and parse it into a pandas dataframe"""

    print('============================')
    print('Downloading BART Daily Station Exits:', url)
    print('============================')
    url = 'http://64.111.127.166/DSE/Daily_Station_Exits.xlsx'
    df_bart = pd.read_excel(url)
    print(df_bart)

    # Then combine and filter data
    df_bart['date'] = pd.to_datetime(df_bart['Date']).dt.date
    df_bart = df_bart.dropna(axis=1, how='all')
    df_bart = df_bart.rename(columns={'Total' : 'total'})

    print('Keeping data from {} onwards'.format(start_date))
    df_bart_filt = df_bart[(df_bart['date'] >= start_date) & (df_bart['total'] > 0)]
    print('Last date of data:', df_bart_filt['date'].max())
    print('Num data points:', len(df_bart_filt))

    num_weeks = len(df_bart_filt) // 7
    df_bart_filt = df_bart_filt[-7*num_weeks:] # number of days is divisble by 7

    df_bart_daily = df_bart_filt.groupby('date')['total'].sum()
    if out_fname:
        print('Saving filtered output to:', out_fname)
        df_bart_daily.to_csv(out_fname)

    assert len(df_bart_daily) % 7 == 0, 'Num days must be a multiple of 7'
    return df_bart_daily, df_bart_filt

def plot_bart_ridership(df_bart_daily):
    perc_normal_ridership_bart = \
        df_bart_daily / np.tile(df_bart_daily[:7].values, len(df_bart_daily) // 7)
    print('% normal ridership:\n', perc_normal_ridership_bart)
    plt.plot(perc_normal_ridership_bart * 100, 'g', label='BART')
    ax = plt.gca()
    fig = plt.gcf()
    fig.autofmt_xdate()
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))

    plt.title('BART Ridership During COVID-19')
    plt.xlabel('Date')
    plt.ylabel('% of normal ridership')
    #plt.legend()
    plt.grid()
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=datetime.date.fromisoformat,
        default=datetime.date(2020,2,1),
        help='approximate start date (default 2020-02-01)')
    parser.add_argument('--out_fname', help='output csv file name to save parsed/filtered ridership data')
    args = parser.parse_args()

    df_bart_daily, df_bart_filt = get_daily_bart_ridership(args.start_date, args.out_fname)
    plot_bart_ridership(df_bart_daily)
