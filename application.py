import pandas as pd
import chart_studio.plotly as py
import plotly
import plotly.graph_objs as go
import dash
from dash import dcc
import dash.html as html
import numpy as np
#import technical_indicators as ts
import pandas as pd
import pandas
import xlsxwriter
import plotly
import quandl
from plotly import tools
from plotly import subplots
import datetime
from dash import dash_table as dt
#from dash_table import DataTable
#import glob

def EMA(df, base, target, period, alpha=False):
    """
    Function to compute Exponential Moving Average (EMA)

    Args :
        df : Pandas DataFrame which contains ['date', 'open', 'high', 'low', 'close', 'volume'] columns
        base : String indicating the column name from which the EMA needs to be computed from
        target : String indicates the column name to which the computed data needs to be stored
        period : Integer indicates the period of computation in terms of number of candles
        alpha : Boolean if True indicates to use the formula for computing EMA using alpha (default is False)

    Returns :
        df : Pandas DataFrame with new column added with name 'target'
    """

    con = pd.concat([df[:period][base].rolling(window=period).mean(), df[period:][base]])

    if (alpha == True):
        # (1 - alpha) * previous_val + alpha * current_val where alpha = 1 / period
        df[target] = con.ewm(alpha=1 / period, adjust=False).mean()
    else:
        # ((current_val - previous_val) * coeff) + previous_val where coeff = 2 / (period + 1)
        df[target] = con.ewm(span=period, adjust=False).mean()

    df[target].fillna(0, inplace=True)
    return df




def ATR(df, period,  ohlc=['Open', 'High', 'Low', 'Close']):
    """
    Function to compute Average True Range (ATR)

    Args :
        df : Pandas DataFrame which contains ['date', 'open', 'high', 'low', 'close', 'volume'] columns
        period : Integer indicates the period of computation in terms of number of candles
        ohlc: List defining OHLC Column names (default ['Open', 'High', 'Low', 'Close'])

    Returns :
        df : Pandas DataFrame with new columns added for
            True Range (TR)
            ATR (ATR_$period)
    """
    atr = 'ATR_' + str(period)

    # Compute true range only if it is not computed and stored earlier in the df
    if not 'TR' in df.columns:
        df['h-l'] = df[ohlc[1]] - df[ohlc[2]]
        df['h-yc'] = abs(df[ohlc[1]] - df[ohlc[3]].shift())
        df['l-yc'] = abs(df[ohlc[2]] - df[ohlc[3]].shift())

        df['TR'] = df[['h-l', 'h-yc', 'l-yc']].max(axis=1)

        df.drop(['h-l', 'h-yc', 'l-yc'], inplace=True, axis=1)

    # Compute EMA of true range using ATR formula after ignoring first row
    EMA(df,'TR', atr, period, alpha=True)
    print(ohlc[3])
    return df


def SuperTrend(df, period, multiplier, ohlc=['Open', 'High', 'Low', 'Close']):
    """
    Function to compute SuperTrend

    Args :
        df : Pandas DataFrame which contains ['date', 'open', 'high', 'low', 'close', 'volume'] columns
        period : Integer indicates the period of computation in terms of number of candles
        multiplier : Integer indicates value to multiply the ATR
        ohlc: List defining OHLC Column names (default ['Open', 'High', 'Low', 'Close'])

    Returns :
        df : Pandas DataFrame with new columns added for
            True Range (TR), ATR (ATR_$period)
            SuperTrend (ST_$period_$multiplier)
            SuperTrend Direction (STX_$period_$multiplier)
    """

    ATR(df, period, ohlc=ohlc)
    atr = 'ATR_' + str(period)
    st = 'ST_' + str(period) + '_' + str(multiplier)
    stx = 'STX_' + str(period) + '_' + str(multiplier)

    """
    SuperTrend Algorithm :

        BASIC UPPERBAND = (HIGH + LOW) / 2 + Multiplier * ATR
        BASIC LOWERBAND = (HIGH + LOW) / 2 - Multiplier * ATR

        FINAL UPPERBAND = IF( (Current BASICUPPERBAND < Previous FINAL UPPERBAND) or (Previous Close > Previous FINAL UPPERBAND))
                            THEN (Current BASIC UPPERBAND) ELSE Previous FINALUPPERBAND)
        FINAL LOWERBAND = IF( (Current BASIC LOWERBAND > Previous FINAL LOWERBAND) or (Previous Close < Previous FINAL LOWERBAND)) 
                            THEN (Current BASIC LOWERBAND) ELSE Previous FINAL LOWERBAND)

        SUPERTREND = IF((Previous SUPERTREND = Previous FINAL UPPERBAND) and (Current Close <= Current FINAL UPPERBAND)) THEN
                        Current FINAL UPPERBAND
                    ELSE
                        IF((Previous SUPERTREND = Previous FINAL UPPERBAND) and (Current Close > Current FINAL UPPERBAND)) THEN
                            Current FINAL LOWERBAND
                        ELSE
                            IF((Previous SUPERTREND = Previous FINAL LOWERBAND) and (Current Close >= Current FINAL LOWERBAND)) THEN
                                Current FINAL LOWERBAND
                            ELSE
                                IF((Previous SUPERTREND = Previous FINAL LOWERBAND) and (Current Close < Current FINAL LOWERBAND)) THEN
                                    Current FINAL UPPERBAND
    """

    # Compute basic upper and lower bands
    df['basic_ub'] = (df[ohlc[1]] + df[ohlc[2]]) / 2 + multiplier * df[atr]
    df['basic_lb'] = (df[ohlc[1]] + df[ohlc[2]]) / 2 - multiplier * df[atr]

    # Compute final upper and lower bands
    df['final_ub'] = 0.00
    df['final_lb'] = 0.00
    for i in range(period, len(df)):
        df['final_ub'].iat[i] = df['basic_ub'].iat[i] if df['basic_ub'].iat[i] < df['final_ub'].iat[i - 1] or \
                                                         df[ohlc[3]].iat[i - 1] > df['final_ub'].iat[i - 1] else \
        df['final_ub'].iat[i - 1]
        df['final_lb'].iat[i] = df['basic_lb'].iat[i] if df['basic_lb'].iat[i] > df['final_lb'].iat[i - 1] or \
                                                         df[ohlc[3]].iat[i - 1] < df['final_lb'].iat[i - 1] else \
        df['final_lb'].iat[i - 1]

    # Set the Supertrend value
    df[st] = 0.00
    for i in range(period, len(df)):
        df[st].iat[i] = df['final_ub'].iat[i] if df[st].iat[i - 1] == df['final_ub'].iat[i - 1] and df[ohlc[3]].iat[
            i] <= df['final_ub'].iat[i] else \
            df['final_lb'].iat[i] if df[st].iat[i - 1] == df['final_ub'].iat[i - 1] and df[ohlc[3]].iat[i] > \
                                     df['final_ub'].iat[i] else \
                df['final_lb'].iat[i] if df[st].iat[i - 1] == df['final_lb'].iat[i - 1] and df[ohlc[3]].iat[i] >= \
                                         df['final_lb'].iat[i] else \
                    df['final_ub'].iat[i] if df[st].iat[i - 1] == df['final_lb'].iat[i - 1] and df[ohlc[3]].iat[i] < \
                                             df['final_lb'].iat[i] else 0.00

        # Mark the trend direction up/down
    df[stx] = np.where((df[st] > 0.00), np.where((df[ohlc[3]] < df[st]), 'down', 'up'), np.NaN)
    df
    # Remove basic and final bands from the columns
    df.drop(['basic_ub', 'basic_lb', 'final_ub', 'final_lb'], inplace=True, axis=1)

    df.fillna(0, inplace=True)

    return df


#Step 2: Bring in data from AKK and read into df

#path = (r'Data')

#filenames = glob.glob(path + "/*.csv")
#print("Reading files from path" + str(path))

#data= []
#for filename in filenames:
    #filename = pd.read_csv(filename)
        #filename = pd.merge(filename, CountryConcord, how='left', left_on='location_name',
                            #right_on='Country name in IHME')
        #filename = pd.merge(filename, SeriesConcord, how='left', left_on='cause_name', right_on='Series name in IHME')
    #filename = filename.dropna(how='any')
        # GBDDalys.append(pd.read_csv(filename,low_memory=False))
    #data.append(filename)

#data = pd.concat(data, ignore_index=True)

#data=pd.read_excel('ProjectUdaan.xlsx')
data9=pd.read_csv('ConsolidatedData.csv')
print(data9.head())
#data1=data1.iloc[2:]
#print(list(data1))
data9.columns=['Symbol', 'Series', 'date', 'Prev Close', 'Open Price', 'High', 'Low', 'Last', 'Close', 'Average Price', 'Total Traded Quantity', 'Turnover', 'No. of Trades','PriceCat']
data9=data9.drop([ 'Series', 'Prev Close', 'Open Price',  'Last',  'Average Price', 'Total Traded Quantity', 'Turnover', 'No. of Trades'],axis=1)
#EMA(data,'open','new',7,alpha=True)
q=data9.Symbol.unique()
print("Done with data process 1")
datatable=data9
#r = pd.melt(r, id_vars=['Symbol','PriceCat','date', 'STX_14_2',], var_name='Type', value_name='values')
#print(r.head())


#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
print("app started")
app = dash.Dash(__name__)
application=app.server

styles = {
    'pre': {
        'border': 'thin lightgrey solid',

    }
}


app.layout =html.Div([html.Div(
    [
        dcc.Markdown(
            '''
            ### Live Dashboard showing super trend computed along with the high and low prices for 50 stocks in the NIFTY index.
            '''.replace('  ', ''),
            className='eight columns offset-by-three'
        )
    ], className='row',
    style={'text-align': 'center', 'margin-bottom': '10px'}
),


        html.Div([(dcc.Dropdown(id='DropDown', options=[{'label': i
, 'value': i} for i in q],value='ADANIPORTS')),
        html.Div(id='container-button-basic',
             children='Please select a stock')],style={ 'width': '20%','float':'right'}),
html.Div([(dcc.Input(id='Input1', value=14)),
        html.Div(id='container-button-basic1',
             children='Please select a period for Super Trend')],style={ 'width': '20%','float':'right'}),
html.Div([(dcc.Input(id='Input2', value=2)),
        html.Div(id='container-button-basic2',
             children='Please select a multiplier for Super Trend')],style={ 'width': '20%','float':'right'}),
html.Div([(dcc.RangeSlider(id='Range',marks={i:'{}'.format(i) for i in range(2012,2022)},min=2013,max=2022,value=[2021,2022],step=1))
          ],style={ 'display': 'inline-block','width': '30%','float':'left','font':'15','height':'52%'}),
      html.Div([dcc.Graph( id='graph',hoverData={'points': [{'x': '31-12-2022'}]})],style={'width': '80%','float':'left','height':'48%', 'display': 'inline-block'}),

])

@app.callback(
    dash.dependencies.Output('graph', 'figure'),
    [dash.dependencies.Input('DropDown', 'value'),
     dash.dependencies.Input('Range', 'value'),
     dash.dependencies.Input('Input1', 'value'),
     dash.dependencies.Input('Input2', 'value')])

def update_fig(value,range1,Input1,Input2):
    print("Fig started")
    #path = (r'C:\Users\kanis\dash_app')

    #filenames = glob.glob(path + "/*.csv")
    #print("Reading files from path" + str(path))
    #print(value)
    #data = []
    #for filename in filenames:
        #filename = pd.read_csv(filename)
        # filename = pd.merge(filename, CountryConcord, how='left', left_on='location_name',
        # right_on='Country name in IHME')
        # filename = pd.merge(filename, SeriesConcord, how='left', left_on='cause_name', right_on='Series name in IHME')
        #filename = filename.dropna(how='any')
        # GBDDalys.append(pd.read_csv(filename,low_memory=False))
        #data.append(filename)

    #data = pd.concat(data, ignore_index=True)

    # data=pd.read_excel('ProjectUdaan.xlsx')
    data9 = pd.read_csv('ConsolidatedData.csv')
    # data1=data1.iloc[2:]
    # print(list(data1))
    data9.columns = ['Symbol', 'Series', 'date', 'Prev Close', 'Open', 'High', 'Low', 'Last', 'Close',
                     'Average Price', 'Total Traded Quantity', 'Turnover', 'No. of Trades','PriceCat']
    data9 = data9.drop(
        ['Series', 'Prev Close','Last', 'Average Price', 'Total Traded Quantity', 'Turnover',
         'No. of Trades'], axis=1)
    print("data9")
    print(data9.head())

    data9=data9[data9["Symbol"]==value]
    #df = df[df.Year.isin(years)]
    Input1=int(Input1)
    Input2=int(Input2)
    print(Input1*1)
    r = SuperTrend(data9, Input1, Input2)
    #r = r.iloc[:2]
    #r = r.iloc[14:]
    #r['PriceCat']=0.00
    #r['PriceCat'] = np.where((r['Close'] > 0.00), np.where((r[r['Prev Close']] < r['Close']), 'down', 'up'), np.NaN)
    #r=r.drop(['Prev Close'])
    min1= min(range1)
    min2=max(range1)
    year2=range(min1,min2)
    r['date'] = pd.to_datetime(r['date'])
    r = r[r['date'].dt.year.isin(year2)]
    # df=df[df.Year.isin(years)]

    print('rhead')
    print(r.head())
    r = pd.melt(r, id_vars=['Symbol','PriceCat','date', 'STX_'+str(Input1)+'_'+str(Input2),], var_name='Type', value_name='values')
    #'Final r'

    #date1=r.drop_duplicates(date1['date'])
    #date=date1['date']
    print("print date")
    #print(date1.head())
    # external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


    opt = ['Open', 'High', 'Low', 'Close']
    data1 = r[r.Type.isin(opt)]

    opt4=['up']
    data1=data1[data1.PriceCat.isin(opt4)]
    #data = data.loc[data['Unit Name'] == 'Percent of GDP']
    print('box plot data before duplicate drop')

    data1.drop_duplicates(subset=['date','Type'])
    x1 = data1['date']
    print('box plot data')



    trace1 = go.Box(
        y=data1['values'],
        x=data1['date'],
        name='Price Range',
        marker=dict(
            color='#3D9970'
        )
    )

    opt = ['Open', 'High', 'Low', 'Close']
    data7 = r[r.Type.isin(opt)]
    opt4 = ['down']
    data7 = data7[data7.PriceCat.isin(opt4)]
    data7.drop_duplicates(subset=['date', 'Type'])
    #x = data7['date']

    trace7 = go.Box(
        y=data7['values'],
        x=data7['date'],
        name='Price Range',
        marker=dict(
            color='rgba(152, 0, 0, .8)'
        )
    )

    opt2 = ['ST_'+str(Input1)+'_'+str(Input2)]
    data2 = r[r.Type.isin(opt2)]
    print('data2Head')
    print(data2.head())
    data2 = data2.loc[data2['STX_'+str(Input1)+'_'+str(Input2)] == 'up']
    data2 = data2.drop_duplicates('date')

    trace2 = go.Scatter(
        y=data2['values'],
        x=data2['date'],
        mode='markers',
        name='SuperTrend Low',
        connectgaps=False,
        marker=dict(
            color='rgba(152, 0, 0, .8)'
        )
    )

    opt4 = ['ST_'+str(Input1)+'_'+str(Input2)]
    data4 = r[r.Type.isin(opt4)]

    data4 = data4.loc[data4['STX_'+str(Input1)+'_'+str(Input2)] == 'down']
    data4 = data4.drop_duplicates('date')

    trace4 = go.Scatter(
        y=data4['values'],
        x=data4['date'],
        mode='markers',
        name='SuperTrend High',
        connectgaps=False,
        marker=dict(
            color='#3D9970'
        )
    )

    opt5 = ['ST_'+str(Input1)+'_'+str(Input2)]
    data5 = r[r.Type.isin(opt5)]

    # data5=data4.loc[data4['STX_7_3']=='down']
    # data4=data4.drop_duplicates('date')
    # print(data4.head())
    trace5 = go.Scatter(
        y=data5['values'],
        x=data5['date'],
        mode='lines',
        name='SuperTrend',
        connectgaps=False,
        marker=dict(
            color='#3D9970'
        )
    )

    opt6 = ['ATR_'+str(Input1)]
    data6 = r[r.Type.isin(opt6)]
    print('data6 heads')

    # data5=data4.loc[data4['STX_7_3']=='down']
    # data4=data4.drop_duplicates('date')
    # print(data4.head())
    trace6 = go.Scatter(
        y=data6['values'],
        x=data6['date'],
        mode='lines',
        name='ATR',
        connectgaps=False,
        marker=dict(
            color='rgb(107,174,214)'
        )
    )

    opt3 = ['Close']
    data3 = r[r.Type.isin(opt3)]

    trace3 = go.Scatter(
        y=data3['values'],
        x=data3['date'],
        name='Closing price',
        mode='markers',
        marker=dict(
            color='rgb(214, 12, 140)'
        )
    )
    print("Data completed")
    data = [trace1,trace7,trace2,trace4,trace5,trace3]


    print('final data')


    fig = subplots.make_subplots(rows=2, cols=1, specs=[[{}], [{}]],
                              shared_xaxes=True, shared_yaxes=True,
                              vertical_spacing=0.001)

    fig.append_trace(trace1, 1, 1)
    fig.append_trace(trace2, 1, 1)
    fig.append_trace(trace3, 1, 1)
    fig.append_trace(trace4, 1, 1)
    fig.append_trace(trace5, 1, 1)
    fig.append_trace(trace7, 1, 1)
    fig.append_trace(trace6, 2, 1)

    fig['layout'].update(height=800, width=1200,
                         title='SuperTrend with ATR for '+str(value))

    return fig



if __name__ == '__main__':
    app.run_server(debug=True)

