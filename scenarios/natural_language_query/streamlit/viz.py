import streamlit as st
import os
import pandas as pd
import sys
sys.path.append('../')
from analyze_v2 import AnalyzeGPT
import openai
import streamlit as st  

from dotenv import load_dotenv

from pathlib import Path  # Python 3.6+ only

faq =["Is that true that top 20% customers generate 80% revenue in 2013?",
      "Which stock items have most seasonality in sales quantity in 2013?", 
      "Which customers are most likely to churn?churn means they have not purchased anything in the last 6 months",
      "show me the revenue trends over the years by sales territory",
      "which brands have the highest revenue by city?",
      "which brands have slowing revenue trend by city in 2013?"
      ]
tables_structure="""
    - Fact.Order(Order_Key(PK),City_Key(FK),Customer_Key(FK),Stock_Item_Key(FK),Order_Date_Key(FK),Picked_Date_Key(FK),Salesperson_Key(FK),Picker_Key(FK),WWI_Order_ID,WWI_Backorder_ID,Description,Package,Quantity,Unit_Price,Tax_Rate,Total_Excluding_Tax,Tax_Amount,Total_Including_Tax,Lineage_Key)
    - Fact.Purchase(Purchase_Key(PK),Date_Key(FK),Supplier_Key(FK),Stock_Item_Key(FK),WWI_Purchase_Order_ID,Ordered_Outers,Ordered_Quantity,Received_Outers,Package,Is_Order_Finalized,Lineage_Key)
    - Fact.Sale(Sale_Key(PK),City_Key(FK),Customer_Key(FK),Bill_To_Customer_Key(FK),Stock_Item_Key(FK),Invoice_Date_Key(FK),Delivery_Date_Key(FK),Salesperson_Key(FK),WWI_Invoice_ID,Description,Package,Quantity,Unit_Price,Tax_Rate,Total_Excluding_Tax,Tax_Amount,Profit,Total_Including_Tax,Total_Dry_Items,Total_Chiller_Items,Lineage_Key)
    - Dimension.City(City_Key(PK),WWI_City_ID,City,State_Province,Country,Continent,Sales_Territory,Region,Subregion,Location,Latest_Recorded_Population,Valid_From,Valid_To,Lineage_Key)
    - Dimension.Customer(Customer_Key(PK),WWI_Customer_ID,Customer,Bill_To_Customer,Category,Buying_Group,Primary_Contact,Postal_Code,Valid_From,Valid_To,Lineage_Key)
    - Dimension.Date(Date(PK),Day_Number,Day,Month,Short_Month,Calendar_Month_Number,Calendar_Month_Label,Calendar_Year,Calendar_Year_Label,Fiscal_Month_Number,Fiscal_Month_Label,Fiscal_Year,Fiscal_Year_Label,ISO_Week_Number)
    - Dimension.Stock_Item(Stock_Item_Key(PK),WWI_Stock_Item_ID,Stock_Item,Color,Selling_Package,Buying_Package,Brand,Size,Lead_Time_Days,Quantity_Per_Outer,Is_Chiller_Stock,Barcode,Tax_Rate,Unit_Price,Recommended_Retail_Price,Typical_Weight_Per_Unit,Photo,Valid_From,Valid_To,Lineage_Key)
    - Dimension.Supplier(Supplier_Key(PK),WWI_Supplier_ID,Supplier,Category,Primary_Contact,Supplier_Reference,Payment_Days,Postal_Code,Valid_From,Valid_To,Lineage_Key)
"""

system_message="""
You are a smart AI assistant to help answer marketing analysis questions by querying data from Microsoft SQL Server Database and visualizing data with plotly. 
In the examples below, questions are broken down into one or several  parts to be analyzed and eventually to answer the main question.
The action after each thought can be a data query and data visualization code or it can be final answer. 
Query syntax must be compliant with Microsoft Transact-SQL specification.
"""

few_shot_examples="""
<<Examples to follow:>>
Question: Show me top 3 best selling products in 2013
Thought 1: I need to query revenue for each month in 2013 for top 3 customers from Fact.Sales table and join with Dimension.Customer to get customer information and join with Dimension.Date to get time information. Then I need to group data by month and customer and sort data by revenue. Finally, I need to visualize data using line chart to show monthly revenue trends for each customer.
Action 1: ```SQL\nSELECT   \nc.Customer,   \nd.Calendar_Month_Label,   \nSUM(s.Total_Including_Tax) AS Revenue   \nFROM   \nFact.Sale s   \nJOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key   \nJOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date   \nWHERE   \nd.Calendar_Year = 2013   \nGROUP BY   \nc.Customer,   \nd.Calendar_Month_Label,   \nd.Calendar_Month_Number   \nHAVING   \nc.Customer IN (  \nSELECT TOP 3   \nc.Customer   \nFROM   \nFact.Sale s   \nJOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key   \nJOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date   \nWHERE   \nd.Calendar_Year = 2013   \nGROUP BY   \nc.Customer   \nORDER BY   \nSUM(s.Total_Including_Tax) DESC  \n)   \nORDER BY   \nc.Customer ASC,   \nd.Calendar_Month_Number ASC```, ```Python\nimport plotly.express as px\n\ndef visualize_data(sql_result_df):\n    fig=px.line(sql_result_df, x='Calendar_Month_Label', y='Revenue', color='Customer', title='Monthly Revenue Trends in 2013 for Top 3 Customers')\n    return fig\n```
Observation 1: Region                                      Stock_Item Total_Sales
0    Americas  "The Gu" red shirt XML tag t-shirt (Black) 3XL  1433516.40
1    Americas  "The Gu" red shirt XML tag t-shirt (Black) 3XS  1395759.60
Thought 2: The result answers the question
Action 2: Answer[The result is provided]

Question: Does 20% customer account for 80% of sales?
Thought 1: I need to determine the total sales generated by the company. 
Action 1: ```SQL\nSELECT\nSUM(Total_Including_Tax) AS Total_Revenue\nFROM\nFact.Sale```
Observation 1: 198043439.45
Thought 2: I now need to calculate the total sales for the top 20% of customers.
Action 2: ```SQL\nWITH CustomerSales AS (  \nSELECT   \nc.Customer_Key,   \nSUM(Total_Including_Tax) AS Total_Revenue  \nFROM   \nFact.Sale s  \nJOIN\nDimension.Customer c ON s.Customer_Key = c.Customer_Key  \nGROUP BY   \nc.Customer_Key  \n),   \nTopCustomers AS (  \nSELECT   \ncs.Customer_Key   \nFROM   \nCustomerSales cs   \nWHERE   \ncs.Total_Revenue >= (  \nSELECT   \nTOP 1 PERCENTILE_CONT(0.2) WITHIN GROUP\n(ORDER BY Total_Revenue DESC) OVER ()   \nFROM   \nCustomerSales  \n)  \n)   \nSELECT   \nSUM(s.Total_Including_Tax) AS Top_Revenue   \nFROM   \nFact.Sale s   \nWHERE   \ns.Customer_Key IN (  \nSELECT   \nCustomer_Key   \nFROM   \nTopCustomers)  ```
Observation 2: 102904875.68
Thought 3: Now I need to divide the sales of top 20% customers by total sales
Action 3: ```SQL\nSELECT\n102904875.68 / 198043439.45 AS Result```
Observation 3: 0.51960759702913
Thought 4: Result came back and it is less than 80% so top 20% customers do not account for 80% of sales
Action 4: Answer[No, top 20% customers do not account for 80% of sales]

"""
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)

# Check if secrets.env exists and if not error out
if not os.path.exists("secrets.env"):
    print("Missing secrets.env file with environment variables. Please create one and try again. See README.md for more details")
    exit(1)

# NOTE: You need to create a secret.env file to run this in the same folder with these variables
openai.api_type = "azure"
openai.api_key = os.environ.get("AZURE_OPENAI_API_KEY","OpenAPIKeyMissing")
openai.api_base = os.environ.get("AZURE_OPENAI_ENDPOINT","OpenAPIEndpointMissing")
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
gpt_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME","gpt-35-turbo")
database=os.environ.get("SQL_DATABASE","WorldWideImportersDW")
dbserver=os.environ.get("SQL_SERVER","someazureresource.database.windows.net")
db_user=os.environ.get("SQL_USER","MissingSQLUser")
db_password= os.environ.get("SQL_PASSWORD","MissingSQLPassword")

analyzer = AnalyzeGPT(tables_structure, system_message, few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)

st.sidebar.title('Data Analysis Assistant')

col1, col2  = st.columns((3,1)) 
with st.sidebar:
    option = st.selectbox('FAQs',faq)
    question = st.text_area("Ask me a  question on churn", option)
    if st.button("Submit"):  
        # Call the execute_query function with the user's question 
        analyzer.run(question, col1)