import argparse
import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bart_ridership import get_daily_bart_ridership
from mta_ridership import get_daily_mta_ridership


def plot_combined_ridership(df_bart_daily, df_mta_daily):
    print('Plotting combined ridership...')
    perc_normal_ridership_bart = \
        df_bart_daily / np.tile(df_bart_daily[:7].values, len(df_bart_daily) // 7)
    perc_normal_ridership_mta = \
        df_mta_daily / np.tile(df_mta_daily[:7].values, len(df_mta_daily) // 7)

    print('% normal ridership (BART):\n', perc_normal_ridership_bart)
    print('% normal ridership (MTA):\n', perc_normal_ridership_mta)

    plt.plot(perc_normal_ridership_bart * 100, label='BART')
    plt.plot(perc_normal_ridership_mta * 100, label='MTA')
    ax = plt.gca()
    fig = plt.gcf()
    fig.autofmt_xdate()
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.title('BART (Bay Area) and MTA (NYC) Ridership During COVID-19')
    plt.xlabel('Date')
    plt.ylabel('% of normal ridership')
    plt.legend()
    plt.grid()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=datetime.date.fromisoformat,
        default=datetime.date(2020,2,1),
        help='approximate start date (default 2020-02-01).')
    args = parser.parse_args()

    df_bart_daily, df_bart_filt = get_daily_bart_ridership(args.start_date)
    df_mta_daily, df_mta_filt = get_daily_mta_ridership(args.start_date)
    plot_combined_ridership(df_bart_daily, df_mta_daily)
