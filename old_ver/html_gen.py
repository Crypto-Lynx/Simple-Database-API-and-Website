import pandas as pd

def sql_to_html_func(query_result, html_page_name):
   df = pd.DataFrame()


   table_header = list(vars(query_result[0]).keys())
   table_header.pop(0)
   header_frame = pd.DataFrame(table_header).T
   df = pd.concat([df, header_frame])


   for row_class in query_result:
       row_table = list(vars(row_class).values())
       row_table.pop(0)  # PK


       df2 = pd.DataFrame(row_table).T
       df = pd.concat([df, df2])


   df.to_html('templates/'+html_page_name+'.html')
