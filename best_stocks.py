import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

@st.cache_data
def get_sp500_symbols():
    """Fetches S&P 500 symbols and caches them."""
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    sp500_df = pd.read_csv(url)
    return sp500_df['Symbol'].tolist()

@st.cache_data
def get_market_caps(symbols):
    """Fetch market caps in batches and sort by size for the top 500."""
    companies = []
    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            market_cap = stock.info.get('marketCap', 0)
            if market_cap:
                companies.append({'Symbol': symbol, 'Market Cap': market_cap})
        except Exception as e:
            st.write(f"Error fetching data for {symbol}: {e}")
    companies_df = pd.DataFrame(companies).sort_values(by='Market Cap', ascending=False)
    return companies_df['Symbol'].tolist()[:500]

def get_covered_calls(stock_symbols, min_premium_ratio=0.03, max_expiration_days=8):
    results = []
    for symbol in stock_symbols:
        stock = yf.Ticker(symbol)
        try:
            current_price = stock.history(period="1d")['Close'][0]
        except (IndexError, KeyError, ValueError) as e:
            st.write(f"Skipping {symbol}: {e}")
            continue

        # Fetch only valid dates and filter by days until expiration
        valid_dates = [
            date for date in stock.options
            if (datetime.strptime(date, '%Y-%m-%d') - datetime.now()).days <= max_expiration_days
        ]

        for date in valid_dates:
            try:
                options = stock.option_chain(date).calls
                options['premium_ratio'] = options['bid'] / current_price
                filtered_options = options[
                    (options['premium_ratio'] >= min_premium_ratio) & (options['strike'] > current_price)
                ]
                for _, row in filtered_options.iterrows():
                    results.append({
                        'Symbol': symbol,
                        'Expiration Date': date,
                        'Strike Price': row['strike'],
                        'Bid Price': row['bid'],
                        'Premium Ratio (%)': round(row['premium_ratio'] * 100, 2),
                        'Current Price': round(current_price, 2)
                    })
            except Exception as e:
                st.write(f"Error processing options for {symbol} on {date}: {e}")

    # Sort results and drop duplicates
    results_df = pd.DataFrame(results).sort_values(by='Premium Ratio (%)', ascending=False)
    results_df = results_df.drop_duplicates(subset=['Symbol'], keep='first')
    return results_df

# Streamlit UI components
st.title("Top S&P 500 Companies with Covered Calls")

min_premium_ratio = st.number_input("Minimum Premium Ratio (%)", min_value=0.0, value=3.0) / 100
max_expiration_days = st.number_input("Max Expiration Days", min_value=1, max_value=30, value=8)

# Fetch data and calculate covered calls
if st.button("Get Covered Calls"):
    all_symbols = get_sp500_symbols()
    top_companies = get_market_caps(all_symbols)
    covered_calls = get_covered_calls(top_companies, min_premium_ratio=min_premium_ratio, max_expiration_days=max_expiration_days)

    # Display the results in a table
    st.subheader("Covered Calls Results")
    if not covered_calls.empty:
        st.table(covered_calls)
    else:
        st.write("No covered calls found that meet the criteria.")
