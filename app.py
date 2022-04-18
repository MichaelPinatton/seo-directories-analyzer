# SEO - Directories Analyzer
# V1 - April 2022
# By Michael Pinatton @michaelpinatton


#import libraries
import streamlit as st
import pandas as pd
import plotly.express as px
from urllib.parse import parse_qs, unquote, urlsplit
import xlsxwriter
from io import BytesIO

#add url_to_df function
def url_to_df(urls, decode=True):
    """Split the given URLs into their components to a DataFrame.

    Each column will have its own component, and query parameters and
    directories will also be parsed and given special columns each.

    :param url urls: A list of URLs to split into components
    :param bool decode: Whether or not to decode the given URLs
    :return DataFrame split: A DataFrame with a column for each component
    """
    if isinstance(urls, str):
        urls = [urls]
    decode = unquote if decode else lambda x: x
    split_list = []
    for url in urls:
        split = urlsplit(decode(url))
        port = split.port
        hostname = split.hostname if split.hostname != split.netloc else None
        split = split._asdict()
        if hostname:
            split['hostname'] = hostname
        if port:
            split['port'] = port
        parsed_query = parse_qs(split['query'])
        parsed_query = {'query_' + key: '@@'.join(val)
                        for key, val in parsed_query.items()}
        split.update(**parsed_query)
        dirs = split['path'].strip('/').split('/')
        if dirs[0]:
            dir_cols = {'dir_{}'.format(n): d for n, d in enumerate(dirs, 1)}
            split.update(**dir_cols)
        split_list.append(split)
    df = pd.DataFrame(split_list)

    query_df = df.filter(regex='query_')
    if not query_df.empty:
        sorted_q_params = (query_df
                           .notna()
                           .mean()
                           .sort_values(ascending=False).index)
        query_df = query_df[sorted_q_params]
        df = df.drop(query_df.columns, axis=1)
    dirs_df = df.filter(regex='^dir_')
    if not dirs_df.empty:
        df = df.drop(dirs_df.columns, axis=1)
        dirs_df = (dirs_df
                   .assign(last_dir=dirs_df
                   .fillna(method='ffill', axis=1)
                   .iloc[:, -1:]
                   .squeeze()))
    df = pd.concat([df, dirs_df, query_df], axis=1)
    df.insert(0, 'url', [decode(url) for url in urls])
    return df

#app config
st.set_page_config(page_title="SEO - Directories Analyzer", layout="wide")

#header
st.title("SEO - Directories Analyzer")
st.subheader("Quick analysis of your directories traffic and performances")
st.write("With this app you'll get data and pie charts for each directory level (1,2 & 3) + insights from directories POV (distribution, CTR, nb of URL, clicks per page)")
st.write("⭐ **Detect in a few minutes your worst and best performing directories** ⭐")

st.markdown(
        "Made by [@MichaelPinatton](https://twitter.com/michaelpinatton) with [![this is an image link](https://i.imgur.com/iIOA6kU.png)](https://www.streamlit.io/) "
    )

with st.expander("🛠️ -- How to use the app?", expanded=False):
    st.markdown("")
    st.markdown(
        """
1. Export the "Landing page" report from Search Console in **CSV format**:
  * From the web Search Console (limited to 1000 URL)
  * From custom Data Studio [like this one](https://datastudio.google.com/reporting/c016a6cd-2c8d-4c7c-9b29-609c94d3015d) (right-click > export CSV)
2. Upload your CSV file on the app
3. Visualize (+download) the 3 pie charts and download the final Excel file
	    """)
    st.markdown("")

with st.expander("ℹ️  -- More info", expanded=False):
    st.markdown("")
    st.markdown(
        """
1. The script doesn't work well with subdomains (better to use URL SC property or domain without subdomain data)
2. In the future, I'd like to add the Search Console API access for a faster experience
3. Thank you [@Elias Dabbas](https://twitter.com/eliasdabbas) for your 'url to df' function I reused here
4. App is in beta, feedbacks are welcome!
	    """)
with st.expander("🐶  -- Examples", expanded=False):

    st.image("ex-pie-chart.png", width=800, caption='Pie chart example')
    st.image("ex-excel.png", width=800, caption='Excel worksheet example')

    st.markdown("")

st.subheader('1) Upload data')

#upload dataframe
input_file = st.file_uploader('Upload your Search Console landing report in CSV format')

#Create DF for CSV, for directories and merge them
if input_file is not None:
    sc = pd.read_csv(input_file)
    sc = sc.rename(columns={'Pages les plus populaires': 'Landing Page','Top pages': 'Landing Page', 'Clics': 'Url Clicks', 'Clicks': 'Url Clicks'})
    sc = sc[['Landing Page','Url Clicks','Impressions']]
    sc = sc.rename(columns={'Url Clicks': 'Clicks'})
    urls =  sc['Landing Page'].tolist()
    directories = url_to_df(urls)
    directories = directories[['url','scheme','netloc','path','dir_1','dir_2','dir_3']]
    full = pd.merge(directories,sc,left_on='url', right_on='Landing Page', how='right')
    full['nb'] = 1
    full[['Clicks', 'Impressions']] = full[['Clicks', 'Impressions']].apply(pd.to_numeric)

    st.subheader('2) Visualize & grab the directories pie charts')

    #Pivot dataframe for directory level 1
    pivot1 = full.pivot_table(
        index=['dir_1'],
        values=['nb', 'Clicks', 'Impressions'],
        aggfunc={'nb': ['sum'], 'Clicks': ['sum'], 'Impressions': ['sum']})
    pivot_dir_1 = pivot1.reset_index()
    pivot_dir_1 = pivot_dir_1.droplevel(1, axis=1)
    pivot_dir_1.rename(columns={'dir_1': 'Dir_1'}, inplace=True)
    pivot_dir_1.rename(columns={'nb': 'Nb_URL'}, inplace=True)
    pivot_dir_1 = pivot_dir_1.sort_values(by='Clicks', ascending=False, na_position='last')
    pivot_dir_1 = pivot_dir_1.reset_index(drop=True)
    pivot_dir_1['Clicks_per_URL'] = pivot_dir_1['Clicks'] / pivot_dir_1['Nb_URL']
    pivot_dir_1['Clicks_per_URL'] = pivot_dir_1['Clicks_per_URL'].round(decimals = 2)
    pivot_dir_1['Dir1_CTR'] = pivot_dir_1['Clicks'] / pivot_dir_1['Impressions']
    pivot_dir_1['Dir1_CTR'] = pivot_dir_1['Dir1_CTR'].round(decimals = 3)
    pivot_dir_1['%_Clicks'] = pivot_dir_1['Clicks'] / pivot_dir_1['Clicks'].sum()
    pivot_dir_1['%_Clicks'] = pivot_dir_1['%_Clicks'].round(decimals = 3)
    pivot_dir_1 = pivot_dir_1[['Dir_1','Clicks', '%_Clicks','Impressions','Dir1_CTR','Nb_URL','Clicks_per_URL']]

    #Pivot dataframe for directory level 2
    pivot2 = full.pivot_table(
        index=['dir_1', 'dir_2'],
        values=['Clicks', 'Impressions', 'nb'],
        aggfunc={'Clicks': ['sum'], 'Impressions': ['sum'], 'nb': ['sum']}
    )
    pivot_dir_2 = pivot2.reset_index()
    pivot_dir_2 = pivot_dir_2.droplevel(1, axis=1)
    pivot_dir_2.rename(columns={'dir_1': 'Dir_1'}, inplace=True)
    pivot_dir_2.rename(columns={'dir_2': 'Dir_2'}, inplace=True)
    pivot_dir_2.rename(columns={'nb': 'Nb_URL'}, inplace=True)
    pivot_dir_2 = pivot_dir_2.sort_values(by='Clicks', ascending=False, na_position='last')
    pivot_dir_2 = pivot_dir_2.reset_index(drop=True)
    pivot_dir_2['Clicks_per_URL'] = pivot_dir_2['Clicks'] / pivot_dir_2['Nb_URL']
    pivot_dir_2['Clicks_per_URL'] = pivot_dir_2['Clicks_per_URL'].round(decimals = 2)
    pivot_dir_2['Dir2_CTR'] = pivot_dir_2['Clicks'] / pivot_dir_2['Impressions']
    pivot_dir_2['Dir2_CTR'] = pivot_dir_2['Dir2_CTR'].round(decimals = 3)
    pivot_dir_2['%_Clicks'] = pivot_dir_2['Clicks'] / pivot_dir_1['Clicks'].sum()
    pivot_dir_2['%_Clicks'] = pivot_dir_2['%_Clicks'].round(decimals = 3)
    pivot_dir_2 = pivot_dir_2[['Dir_1','Dir_2','Clicks','%_Clicks','Impressions','Dir2_CTR','Nb_URL','Clicks_per_URL']]

    #Pivot dataframe for directory level 3
    pivot3 = full.pivot_table(
        index=['dir_1', 'dir_2', 'dir_3'],
        values=['Clicks', 'Impressions', 'nb'],
        aggfunc={'Clicks': ['sum'], 'Impressions': ['sum'], 'nb': ['sum']}
    )
    pivot_dir_3 = pivot3.reset_index()
    pivot_dir_3 = pivot_dir_3.droplevel(1, axis=1)
    pivot_dir_3.rename(columns={'dir_1': 'Dir_1'}, inplace=True)
    pivot_dir_3.rename(columns={'dir_2': 'Dir_2'}, inplace=True)
    pivot_dir_3.rename(columns={'dir_3': 'Dir_3'}, inplace=True)
    pivot_dir_3.rename(columns={'nb': 'Nb_URL'}, inplace=True)
    pivot_dir_3 = pivot_dir_3.sort_values(by='Clicks', ascending=False, na_position='last')
    pivot_dir_3 = pivot_dir_3.reset_index(drop=True)
    pivot_dir_3['Clicks_per_URL'] = pivot_dir_3['Clicks'] / pivot_dir_3['Nb_URL']
    pivot_dir_3['Clicks_per_URL'] = pivot_dir_3['Clicks_per_URL'].round(decimals = 2)
    pivot_dir_3['Dir3_CTR'] = pivot_dir_3['Clicks'] / pivot_dir_3['Impressions']
    pivot_dir_3['Dir3_CTR'] = pivot_dir_3['Dir3_CTR'].round(decimals = 3)
    pivot_dir_3['%_Clicks'] = pivot_dir_3['Clicks'] / pivot_dir_1['Clicks'].sum()
    pivot_dir_3['%_Clicks'] = pivot_dir_3['%_Clicks'].round(decimals = 3)
    pivot_dir_3 = pivot_dir_3[['Dir_1','Dir_2','Dir_3', 'Clicks','%_Clicks','Impressions','Dir3_CTR','Nb_URL','Clicks_per_URL']]

    #Calculate average CTR
    average_ctr_dir_1 = pivot_dir_1['Clicks'].sum() / pivot_dir_1['Impressions'].sum()
    average_ctr_dir_2 = pivot_dir_2['Clicks'].sum() / pivot_dir_2['Impressions'].sum()
    average_ctr_dir_3 = pivot_dir_3['Clicks'].sum() / pivot_dir_3['Impressions'].sum()

    #Plot for directories level 1
    pivot_dir_1_plot = pivot_dir_1[['Dir_1','%_Clicks']]
    pivot_dir_1_plot = pivot_dir_1_plot.drop(pivot_dir_1_plot[pivot_dir_1_plot['%_Clicks'] == 0].index)
    pivot_dir_1_plot.loc[pivot_dir_1_plot['%_Clicks'] < 0.005, 'Dir_1'] = '*others'
    plot_dir_1 = px.pie(pivot_dir_1_plot, values='%_Clicks', names='Dir_1', title='Click distribution for Directories level 1', width=1200, height=600)
    st.plotly_chart(plot_dir_1, use_container_width=True)

    #Plot for directories level 2
    pivot_dir_2_plot = pivot_dir_2[['Dir_1','Dir_2','%_Clicks']]
    pivot_dir_2_plot = pivot_dir_2_plot.drop(pivot_dir_2_plot[pivot_dir_2_plot['%_Clicks'] == 0].index)
    pivot_dir_2_plot['Dir_2'] = pivot_dir_2_plot['Dir_1'] + '/' + pivot_dir_2_plot['Dir_2']
    pivot_dir_2_plot.loc[pivot_dir_2_plot['%_Clicks'] < 0.005, 'Dir_2'] = '*others'
    pivot_dir_2_plot = pivot_dir_2_plot[['Dir_2','%_Clicks']]
    plot_dir_2 = px.pie(pivot_dir_2_plot, values='%_Clicks', names='Dir_2', title='Click distribution for Directories level 2', width=1300, height=600)
    st.plotly_chart(plot_dir_2, use_container_width=True)

    #Plot for directories level 3
    pivot_dir_3_plot = pivot_dir_3[['Dir_1','Dir_2','Dir_3','%_Clicks']]
    pivot_dir_3_plot = pivot_dir_3_plot.drop(pivot_dir_3_plot[pivot_dir_3_plot['%_Clicks'] == 0].index)
    pivot_dir_3_plot['Dir_3'] = pivot_dir_3_plot['Dir_1'] + '/' + pivot_dir_3_plot['Dir_2'] + '/' + pivot_dir_3_plot['Dir_3']
    pivot_dir_3_plot.loc[pivot_dir_3_plot['%_Clicks'] < 0.005, 'Dir_3'] = '*others'
    pivot_dir_3_plot = pivot_dir_3_plot[['Dir_3','%_Clicks']]
    plot_dir_3 = px.pie(pivot_dir_3_plot, values='%_Clicks', names='Dir_3', title='Click distribution for Directories level 3', width=1400, height=600)
    st.plotly_chart(plot_dir_3, use_container_width=True)

    #EXPORT EXCEL FILE
    output = BytesIO()

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Write each dataframe to a different worksheet + styling

    workbook = writer.book

    format_center = workbook.add_format()
    format_center.set_align('center')

    sup_mean = workbook.add_format()
    sup_mean.set_font_color('green')

    minus_mean = workbook.add_format()
    minus_mean.set_font_color('red')

    sc.to_excel(writer, sheet_name='Data_SC')
    worksheet = writer.sheets['Data_SC']
    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:C', 100)
    worksheet.set_column('C:D', 15, format_center)

    pivot_dir_1.to_excel(writer, sheet_name='Dir_1')
    worksheet = writer.sheets['Dir_1']
    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:B', 40)
    worksheet.set_column('C:H', 15, format_center)

    worksheet.conditional_format('F2:F50000', {'type':     'cell',
                                            'criteria': '>',
                                            'value':    average_ctr_dir_1,
                                            'format':   sup_mean})

    worksheet.conditional_format('F2:F50000', {'type':     'cell',
                                            'criteria': '<',
                                            'value':    average_ctr_dir_1,
                                            'format':   minus_mean})

    worksheet.conditional_format('H2:H50000', {'type': '3_color_scale',
                                             'min_color': "#F8696B",
                                              'mid_color': "#FFEB84",
                                             'max_color': "#63BE7B"})

    pivot_dir_2.to_excel(writer, sheet_name='Dir_2')
    worksheet = writer.sheets['Dir_2']
    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:C', 40)
    worksheet.set_column('D:I', 15, format_center)

    worksheet.conditional_format('G2:G50000', {'type':     'cell',
                                            'criteria': '>',
                                            'value':    average_ctr_dir_2,
                                            'format':   sup_mean})

    worksheet.conditional_format('G2:G50000', {'type':     'cell',
                                            'criteria': '<',
                                            'value':    average_ctr_dir_2,
                                            'format':   minus_mean})

    worksheet.conditional_format('I2:I50000', {'type': '3_color_scale',
                                             'min_color': "#F8696B",
                                              'mid_color': "#FFEB84",
                                             'max_color': "#63BE7B"})

    pivot_dir_3.to_excel(writer, sheet_name='Dir_3')
    worksheet = writer.sheets['Dir_3']
    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:D', 40)
    worksheet.set_column('E:J', 15, format_center)

    worksheet.conditional_format('H2:H50000', {'type':     'cell',
                                            'criteria': '>',
                                            'value':    average_ctr_dir_3,
                                            'format':   sup_mean})

    worksheet.conditional_format('H2:H50000', {'type':     'cell',
                                            'criteria': '<',
                                            'value':    average_ctr_dir_3,
                                            'format':   minus_mean})

    worksheet.conditional_format('J2:J50000', {'type': '3_color_scale',
                                             'min_color': "#F8696B",
                                              'mid_color': "#FFEB84",
                                             'max_color': "#63BE7B"})

    # Close the Pandas Excel writer and output the Excel file.
    writer.save()

    st.subheader('3) Download the Excel file')

    #Download Excel file
    st.download_button(
    label="Click to download the Excel file",
    data=output.getvalue(),
    file_name="SEO_Directories_Analyzer.xlsx",
    mime="application/vnd.ms-excel")

else:
    pass
