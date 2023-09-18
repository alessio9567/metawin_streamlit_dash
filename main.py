import os
import datetime
import numpy as np
from flipside import Flipside
import pandas as pd
import plotly.express as px
import streamlit as st

file_name = 'metawin_transactions_all_time.csv'
file_path = f"{os.getcwd()}\\{file_name}"

# Get the current date
today = pd.Timestamp('today').date()

def auto_paginate_result(query_result_set, page_size=10000):
    """
    This function auto-paginates a query result to get all the data. It assumes 10,000 rows per page.
    In case of an error, reduce the page size. Uses numpy.
    """
    num_rows = query_result_set.page.totalRows
    page_count = np.ceil(num_rows / page_size).astype(int)
    all_rows = []
    current_page = 1
    while current_page <= page_count:
        results = flipside.get_query_results(
            query_result_set.query_id,
            page_number=current_page,
            page_size=page_size
        )

        if results.records:
            all_rows.extend(results.records)  # Use extend() to add list elements

        current_page += 1  # Increment the current page number

    return all_rows  # Return all_rows in JSON format


if not os.path.exists(file_path):
    # Initialize `Flipside` with your API Key and API Url
    flipside = Flipside("a3e63b6a-b082-4528-ba6d-46878fd616bb", "https://api-v2.flipsidecrypto.xyz")

    STARTING_DATE = "'2022-01-01'"

    sql = f""" 
        with metawin_txs AS (
      SELECT
        *,
        concat(contract_address, '_', decoded_log:raffleId) AS raffle_id
      FROM
        ethereum.core.fact_decoded_event_logs
      WHERE
        contract_address IN (
          SELECT
            DISTINCT contract_address
          FROM
            ethereum.core.fact_decoded_event_logs
          WHERE
            decoded_log:"role" IN (
              '0x523a704056dcd17bcf83bed8b68c59416dac1119be77755efe3bde0a64e46e0c',
              '0xde5ee446972f4e39ab62c03aa34b2096680a875c3fdb3eb2f947cbb93341c058'
            )
            and decoded_log:"sender" = '0x3684a8007dc9df696a86b0c5c89a8032b78b5b0d'
            AND block_timestamp > {STARTING_DATE}
        )
        AND block_timestamp > {STARTING_DATE}
    )
    SELECT
      date_trunc('week', v1.block_timestamp) tx_dt,
      contract_address,
      event_name,
      count(DISTINCT v1.tx_hash) AS tot_txs_count,
      SUM(v2.tx_fee) AS weekly_eth_fee,
      weekly_eth_gas_fee_paid / weekly_txs_count AS avg_gas_eth_gas_fee_paid_by_smart_contract,
      AVG(avg_gas_eth_gas_fee_paid_by_smart_contract) OVER(ORDER BY tx_dt)
    FROM
      metawin_txs v1
      JOIN ethereum.core.fact_transactions v2 ON v1.tx_hash = v2.tx_hash
    WHERE
      v2.block_timestamp > {STARTING_DATE}
    GROUP BY
      1,
      2,
      3
    """

    # Run the query against Flipside's query engine and await the results
    query_result_set = flipside.query(sql)

    df = auto_paginate_result(query_result_set)

    df = pd.DataFrame(
        df)

    df.to_csv(file_name, ',')

else:
    df = pd.read_csv(file_path)


# Convert the date column to a datetime format
df['tx_dt'] = pd.to_datetime(df['tx_dt']).dt.date

# Set the dash title
st.title(  "MetaWin Dashboard 🎰📊" )

# Time period selector
time_period_options = ["Last 7 days", "Last month", "Last 3 months", "Last year", "This year", "All time"]
time_period = st.selectbox("Select time period:", time_period_options)

# Tabs
tabs = st.tabs(["Transactions 📊", "Users 👤", "Gas Fees ⛽ ", "Tickets 🎫"])

# Filter the data by time period
if time_period == 'Last 7 days':
    df_filtered = df[df['tx_dt'] > today - datetime.timedelta(days=7)]
elif time_period == 'Last month':
    df_filtered = df[df['tx_dt'] > today - datetime.timedelta(days=30)]
elif time_period == 'Last 3 months':
    df_filtered = df[df['tx_dt'] > today - datetime.timedelta(days=90)]
elif time_period == 'Last year':
    df_filtered = df[df['tx_dt'] > today - datetime.timedelta(days=365)]
elif time_period == 'This year':
    df_filtered = df[df['tx_dt'] > today.replace(month=1, day=1)]
else:
    df_filtered = df

# Sorting Df values by Date in ascending order
df = df.sort_values(by=['tx_dt'], ascending=True)

# Transactions tab
with tabs[0]:

    # Total number of transactions
    total_transaction_count = df_filtered["tot_txs_count"].sum()
    st.write("Total Number of Transactions:", total_transaction_count)

    # Plot the number of transactions per week by event
    fig = px.bar(
        df_filtered,
        x="tx_dt",
        y="tot_txs_count",
        title="Weekly Number of Transactions by Event ({})".format(time_period),
        width=800,
        height=400,
        color="event_name",
        labels={"tx_dt":"Week","tot_txs_count":"Number of Transactions"}
    )

    st.plotly_chart(fig)

    # Weekly number of transactions by smart contract
    fig = px.bar(
        df_filtered,
        x="tx_dt",
        y="tot_txs_count",
        title="Weekly Number of Transactions by Smart Contract ({})".format(time_period),
        width=800,
        height=400,
        color="contract_address",
        labels={"tx_dt":"Week","tot_txs_count":"Number of Transactions"}
    )

    st.plotly_chart(fig)


# Gas Fees tab
with tabs[2]:

    # Total volume of ETH Gas Fees
    total_eth_gas_fee = df_filtered["weekly_eth_fee"].sum()
    st.write("Total ETH Gas Fees Generated:", total_eth_gas_fee)

    # Plot the volume of ETH Gas Fee per week
    fig = px.bar(
        df_filtered,
        x="tx_dt",
        y="weekly_eth_fee",
        title="Weekly Volume of ETH Gas Fee ({})".format(time_period),
        width=800,
        height=400,
        labels={"tx_dt":"Week","weekly_eth_fee":"ETH"}
    )

    st.plotly_chart(fig)

    # Plot the volume of ETH Gas Fee per week by smart contract
    fig = px.bar(
        df_filtered,
        x="tx_dt",
        y="weekly_eth_fee",
        title="Weekly Volume of ETH Gas Fee by Smart Contract ({})".format(time_period),
        width=800,
        height=400,
        color="contract_address",
        labels={"tx_dt":"Week","weekly_eth_fee":"ETH"}
    )

    st.plotly_chart(fig)

    # Moving Average ETH Gas Fee by Smart Contract (only EntrySold action)

    # filtering by event_name = 'EntrySold'
    df_filtered = df_filtered[df_filtered["event_name"] == 'EntrySold']

    df_filtered["weekly_avg_eth_gas_fee_paid_by_smart_contract"] = df_filtered["weekly_eth_fee"]/df_filtered["tot_txs_count"]

    df_filtered["ma_eth_gas_fee"] = df_filtered.groupby('tx_dt')['weekly_avg_eth_gas_fee_paid_by_smart_contract'].transform(pd.Series.mean)

    # Plot the Moving Average ETH Gas Fee (only EntrySold event)
    fig = px.scatter(
        df_filtered,
        x="tx_dt",
        y="ma_eth_gas_fee",
        title="Moving Average ETH Gas Fee (only EntrySold event) ({})".format(time_period),
        width=800,
        height=400,
        labels={"tx_dt":"Week","ma_eth_gas_fee":"ETH"}
    )

    st.plotly_chart(fig)




# Users tab
# Raffle and tickets tab