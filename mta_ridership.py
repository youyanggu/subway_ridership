import argparse
import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Based on MTA turnstile data: http://web.mta.info/developers/turnstile.html

pd.plotting.register_matplotlib_converters()
pd.options.mode.chained_assignment = None

def text_to_df(text):
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

def get_daily_mta_ridership(start_date, out_fname=None):
    # First download raw data from MTA website
    print('Fetching data starting on {}'.format(start_date))
    print('Might take a minute or two...')
    assert start_date.weekday() == 5, 'Start date must be a Saturday'
    date = start_date - datetime.timedelta(days=7) # we start from the week before
    dfs = []
    while date <= datetime.date.today():
        url = 'http://web.mta.info/developers/data/nyct/turnstile/turnstile_{}.txt'.format(
            date.strftime('%y%m%d'))
        date += datetime.timedelta(days=7)
        print(url)
        resp = requests.get(url)
        print(resp, len(resp.text))

        data = resp.text
        df = text_to_df(data)
        dfs.append(df)

    # Then combine and filter data
    print('Combining and filtering data...')
    df_all = pd.concat(dfs)
    df_all['date'] = pd.to_datetime(df_all['DATE']).dt.date
    df_all = df_all[df_all['date'] >= start_date + datetime.timedelta(days=6)]
    df_all['ENTRIES'] = df_all['ENTRIES'].astype(int)
    df_all['EXITS'] = df_all['EXITS'].astype(int)

    sort_cols = ['C/A', 'UNIT', 'SCP', 'STATION', 'LINENAME', 'DIVISION', 'DATE']
    df_all = df_all.sort_values(sort_cols).reset_index()
    df_daily = df_all.drop_duplicates(sort_cols, keep='last').reset_index()
    df_daily['entries_daily'] = df_daily.groupby(sort_cols[:-1])['ENTRIES'].diff()
    df_daily['exits_daily'] = df_daily.groupby(sort_cols[:-1])['EXITS'].diff()

    df_mta_filt = df_daily[(df_daily['entries_daily'] >= 0) & (df_daily['entries_daily'] < 20000) &
        (df_daily['exits_daily'] >= 0) & (df_daily['exits_daily'] < 20000)]

    df_mta_daily = df_mta_filt.groupby('date')['entries_daily'].sum()
    if out_fname:
        print('Saving filtered output to:', out_fname)
        df_mta_daily.to_csv(out_fname)

    assert len(df_mta_daily) % 7 == 0, len(df_mta_daily)
    return df_mta_daily

def plot_mta_ridership(df_mta_daily):
    perc_normal_ridership_mta = \
        df_mta_daily / np.tile(df_mta_daily[:7].values, len(df_mta_daily) // 7)
    print('% normal ridership:\n', perc_normal_ridership_mta)
    plt.plot(perc_normal_ridership_mta * 100, label='MTA')
    # Optional: filter by station name
    #g34 = df_mta_daily[df_mta_daily['STATION'] == '34 ST-HERALD SQ'].groupby('date')['entries_daily'].sum()
    #plt.plot(g34, label='34th St')
    ax = plt.gca()
    fig = plt.gcf()
    fig.autofmt_xdate()
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.title('NYC MTA Ridership During COVID-19')
    plt.xlabel('Date')
    plt.ylabel('% of normal ridership')
    #plt.legend()
    plt.grid()
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=datetime.date.fromisoformat,
        default=datetime.date(2020,2,1),
        help='approximate start date (default 2020-02-01).')
    parser.add_argument('--out_fname', help='output csv file name to save parsed/filtered ridership data')
    args = parser.parse_args()

    df_mta_daily = get_daily_mta_ridership(args.start_date, args.out_fname)
    plot_mta_ridership(df_mta_daily)
