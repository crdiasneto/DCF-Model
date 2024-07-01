import yfinance as yf
import pandas as pd
import streamlit as st

def cashflow(ticker):
    stock = yf.Ticker(ticker)
    cashflow = stock.cashflow
    return cashflow

def historical_free_cashflow(cashflow):
    historical_fcf = cashflow.loc['Free Cash Flow']
    historical_fcf = pd.to_numeric(historical_fcf, errors='coerce')  # Convert to numeric, coerce errors to NaN
    historical_fcf = historical_fcf.dropna()  # Drop any NaN values
    historical_fcf.index = pd.to_datetime(historical_fcf.index).year  # Convert index to datetime and extract year
    historical_fcf = historical_fcf.iloc[::-1]  # Reverse the order
    return historical_fcf

def historical_fcf_percentage(historical_fcf):
    historical_fcf_percentage = historical_fcf.pct_change(fill_method=None).dropna() * 100
    historical_fcf_percentage = historical_fcf_percentage.mean()
    return historical_fcf_percentage

def future_cashflow(historical_fcf, rate): # Don't forget to create an input for rate
    FFCF_Series = pd.Series(index=range(len(historical_fcf) + 1))
    FFCF_Series[0] = historical_fcf.iloc[-1]
    for i in range(len(historical_fcf)):
        FFCF_Series[i+1] = FFCF_Series[i] * (1 + rate)
    return FFCF_Series

def calculate_terminal_value(Current_FCF, Perp_rate, Required_rate):
    terminal_value = Current_FCF * ((1 + Perp_rate) / (Required_rate - Perp_rate))
    return terminal_value

def PV_FCF(FFCF_Series, Required_rate, terminal_value):
    FFCF_List = FFCF_Series.tolist()
    PV_FFCF_List = []

    for i in range(len(FFCF_List)):
        discount_factor = (1 + Required_rate) ** (i + 1)
        discounted_value = FFCF_List[i] / discount_factor
        PV_FFCF_List.append(discounted_value)

    # Adding terminal value discounted to the present
    terminal_value_discounted = terminal_value / (1 + Required_rate) ** len(FFCF_List)
    PV_FFCF_List.append(terminal_value_discounted)

    # Convert the list back to a Series with appropriate index
    PV_FFCF_Series = pd.Series(PV_FFCF_List, index=range(len(PV_FFCF_List)))
    return PV_FFCF_Series

# Streamlit app
st.title('Simple DCF Analysis')

# User inputs
ticker = st.text_input("Enter a ticker symbol:", 'AAPL')
growth_rate = st.number_input("Enter a growth rate:", min_value=0.0, max_value=10.0, value=0.05, step=0.01)
required_rate = st.number_input("Enter a required rate:", min_value=0.0, max_value=1.0, value=0.1, step=0.01)
perp_rate = st.number_input("Enter a perpetual growth rate:", min_value=0.0, max_value=1.0, value=0.02, step=0.01)

if st.button('Analyze'):
    HFCF = historical_free_cashflow(cashflow(ticker))
    st.write(f'Historical Cash Flow for {ticker}')
    st.dataframe(HFCF)

    H_Percentage = float(historical_fcf_percentage(HFCF))
    st.write('Average Historical FCF Growth YOY')
    st.write(f'{round(H_Percentage, 2)}%')

    FFCF_Series = future_cashflow(HFCF, growth_rate)
    terminal_value = calculate_terminal_value(HFCF.iloc[-1], perp_rate, required_rate)
    st.write('Future Cash Flow:')
    st.dataframe(FFCF_Series)

    PV_FFCF_Series = PV_FCF(FFCF_Series, required_rate, terminal_value)
    sum_FFCF = PV_FFCF_Series.sum()
    stock = yf.Ticker(ticker)
    shares_outstanding = stock.info['sharesOutstanding']
    intrinsic_value = sum_FFCF / shares_outstanding
    historical_price = stock.history(period='1d', interval='1m')
    current_price = historical_price['Close'].iloc[-1]
    st.write(f'Current Price for {ticker}: $ {round(current_price, 2)}')
    st.write(f'Intrinsic Value for {ticker}: $ {round(intrinsic_value, 2)}')

    # Excel export
    excel_filename = f"{ticker}_financial_analysis.xlsx"
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        HFCF.to_frame(name='Historical FCF').to_excel(writer, sheet_name='Historical FCF')
        pd.DataFrame({'Future FCF': FFCF_Series}).to_excel(writer, sheet_name='Future FCF')
        pd.DataFrame({'PV of Future FCF': PV_FFCF_Series}).to_excel(writer, sheet_name='PV of Future FCF')
        summary_data = {
            'Metric': ['Average Historical FCF Growth YOY', 'Average Projected FCF Growth YOY', 'Required Rate', 'Current Price', 'Intrinsic Value'],
            'Value': [f'{round(H_Percentage, 2)}%', f'{round(growth_rate * 100, 2)}%', f'{round(required_rate * 100, 2)}%', f'${round(current_price, 2)}', f'${round(intrinsic_value, 2)}']
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary')

    # Add a download button
    with open(excel_filename, 'rb') as file:
        btn = st.download_button(
            label="Download Excel file",
            data=file,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
