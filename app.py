import streamlit as st
import re
import pandas as pd
import os
import io
from datetime import datetime

# ==========================
# Normalization function
# ==========================
def normalize_sql(sql):
    """Normalize SQL text for comparison: lowercase, remove extra spaces, sort SELECT columns."""
    sql = sql.lower().strip().rstrip(";")
    sql = re.sub(r"\s+", " ", sql)
    # Remove aliases: simple heuristic
    sql = re.sub(r"\bas\s+\w+", "", sql)
    sql = re.sub(r"\bfrom\s+(\w+)\s+\w+", r"from \1", sql)

    # Normalize SELECT column order
    if sql.startswith("select"):
        parts = sql.split("from")
        select_part = parts[0].replace("select", "").strip()
        rest = "from" + "from".join(parts[1:]) if len(parts) > 1 else ""
        columns = [c.strip() for c in select_part.split(",")]
        columns.sort()
        sql = "select " + ", ".join(columns) + " " + rest

    return sql

# ==========================
# SQL Question Bank with Enhanced Information
# ==========================
QUESTIONS = [
    {
        "id":1, 
        "question":"Which shippers do we have?", 
        "description": "Display all shipping companies available in the database. This helps identify all carriers used for order deliveries.",
        "tables": ["shippers"],
        "table_info": {
            "shippers": {
                "columns": ["shipperid (INT, PK)", "companyname (VARCHAR)", "phone (VARCHAR)"],
                "sample": "shipperid: 1, companyname: 'Speedy Express', phone: '(503) 555-9831'"
            }
        },
        "solution":"SELECT * FROM shippers"
    },
    {
        "id":2, 
        "question":"Certain fields from Categories", 
        "description": "Extract specific information about product categories. Show the category name and its description to understand product groupings.",
        "tables": ["categories"],
        "table_info": {
            "categories": {
                "columns": ["categoryid (INT, PK)", "categoryname (VARCHAR)", "description (TEXT)"],
                "sample": "categoryid: 1, categoryname: 'Beverages', description: 'Soft drinks, coffees, teas...'"
            }
        },
        "solution":"SELECT categoryname, description FROM categories"
    },
    {
        "id":3, 
        "question":"Sales Representatives", 
        "description": "List all employees who work as Sales Representatives. Display their names and when they were hired to track the sales team.",
        "tables": ["employees"],
        "table_info": {
            "employees": {
                "columns": ["employeeid (INT, PK)", "firstname (VARCHAR)", "lastname (VARCHAR)", "title (VARCHAR)", "hiredate (DATE)"],
                "sample": "employeeid: 1, firstname: 'Nancy', lastname: 'Davolio', title: 'Sales Representative', hiredate: '1992-05-01'"
            }
        },
        "solution":"SELECT firstname, lastname, hiredate FROM employees WHERE title = 'Sales Representative'"
    },
    {
        "id":4, 
        "question":"Sales Representatives in the United States", 
        "description": "Filter sales representatives by country. Identify the US-based sales team for regional management purposes.",
        "tables": ["employees"],
        "table_info": {
            "employees": {
                "columns": ["employeeid (INT, PK)", "firstname (VARCHAR)", "lastname (VARCHAR)", "title (VARCHAR)", "country (VARCHAR)", "hiredate (DATE)"],
                "sample": "employeeid: 1, firstname: 'Nancy', lastname: 'Davolio', title: 'Sales Representative', country: 'USA', hiredate: '1992-05-01'"
            }
        },
        "solution":"SELECT firstname, lastname, hiredate FROM employees WHERE title = 'Sales Representative' AND country = 'USA'"
    },
    {
        "id":5, 
        "question":"Orders placed by specific EmployeeID", 
        "description": "Retrieve all orders handled by a particular employee (ID 5). Used to track individual sales performance and order history.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "employeeid (INT, FK)", "orderdate (DATE)", "shipcountry (VARCHAR)"],
                "sample": "orderid: 10248, customerid: 'VINET', employeeid: 5, orderdate: '1996-07-04', shipcountry: 'France'"
            }
        },
        "solution":"SELECT * FROM orders WHERE employeeid = '5'"
    },
    {
        "id":6, 
        "question":"Suppliers and ContactTitles", 
        "description": "Find suppliers excluding Marketing Managers. Useful for identifying decision makers and procurement contacts at different supplier organizations.",
        "tables": ["suppliers"],
        "table_info": {
            "suppliers": {
                "columns": ["supplierid (INT, PK)", "companyname (VARCHAR)", "contactname (VARCHAR)", "contacttitle (VARCHAR)"],
                "sample": "supplierid: 1, companyname: 'Exotic Liquids', contactname: 'Charlotte Cooper', contacttitle: 'Purchasing Manager'"
            }
        },
        "solution":"SELECT supplierid, contactname, contacttitle FROM suppliers WHERE contacttitle <> 'Marketing Manager'"
    },
    {
        "id":7, 
        "question":"Products with queso in ProductName", 
        "description": "Search for products containing 'queso' in their name. Demonstrates pattern matching for product discovery and inventory management.",
        "tables": ["products"],
        "table_info": {
            "products": {
                "columns": ["productid (INT, PK)", "productname (VARCHAR)", "categoryid (INT, FK)", "unitprice (DECIMAL)"],
                "sample": "productid: 11, productname: 'Queso Cabrales', categoryid: 4, unitprice: 21.00"
            }
        },
        "solution":"SELECT productid, productname FROM products WHERE productname LIKE '%queso%'"
    },
    {
        "id":8, 
        "question":"Orders shipping to France or Belgium", 
        "description": "Find orders going to specific European countries. Useful for regional shipping analysis and logistics planning.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "shipcountry (VARCHAR)", "shippeddate (DATE)"],
                "sample": "orderid: 10248, customerid: 'VINET', shipcountry: 'France', shippeddate: '1996-07-10'"
            }
        },
        "solution":"SELECT orderid, customerid, shipcountry FROM orders WHERE shipcountry = 'France' OR shipcountry = 'Belgium'"
    },
    {
        "id":9, 
        "question":"Orders shipping to any country in Latin America", 
        "description": "Filter orders by multiple countries using IN clause. Demonstrates grouping multiple conditions for regional analysis.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "shipcountry (VARCHAR)"],
                "sample": "orderid: 10259, customerid: 'CENTC', shipcountry: 'Brazil'"
            }
        },
        "solution":"SELECT orderid, customerid, shipcountry FROM orders WHERE shipcountry IN ('Brazil', 'Mexico', 'Argentina', 'Venezuela')"
    },
    {
        "id":10, 
        "question":"Employees, in order of age", 
        "description": "Sort employees by birthdate to identify age demographics and workforce composition. Shows sorting in ascending order.",
        "tables": ["employees"],
        "table_info": {
            "employees": {
                "columns": ["employeeid (INT, PK)", "firstname (VARCHAR)", "lastname (VARCHAR)", "title (VARCHAR)", "birthdate (DATE)"],
                "sample": "employeeid: 9, firstname: 'Anne', lastname: 'Dodsworth', title: 'Sales Representative', birthdate: '1966-01-27'"
            }
        },
        "solution":"SELECT firstname, lastname, title, birthdate FROM employees ORDER BY birthdate"
    },
    {
        "id":11, 
        "question":"Showing only the Date with a DateTime field", 
        "description": "Extract just the date portion from a datetime field. Demonstrates data type casting and formatting for readability.",
        "tables": ["employees"],
        "table_info": {
            "employees": {
                "columns": ["employeeid (INT, PK)", "firstname (VARCHAR)", "lastname (VARCHAR)", "birthdate (DATETIME)"],
                "sample": "birthdate: '1966-01-27 00:00:00' → cast to DATE: '1966-01-27'"
            }
        },
        "solution":"SELECT firstname, lastname, title, CAST(birthdate AS DATE) FROM employees ORDER BY birthdate"
    },
    {
        "id":12, 
        "question":"Employees full name", 
        "description": "Concatenate first and last names to create a full name field. Demonstrates string concatenation for formatted output.",
        "tables": ["employees"],
        "table_info": {
            "employees": {
                "columns": ["employeeid (INT, PK)", "firstname (VARCHAR)", "lastname (VARCHAR)"],
                "sample": "firstname: 'Nancy', lastname: 'Davolio' → fullname: 'Nancy Davolio'"
            }
        },
        "solution":"SELECT firstname, lastname, firstname + ' ' + lastname AS fullname FROM employees"
    },
    {
        "id":13, 
        "question":"OrderDetails amount per line item", 
        "description": "Calculate the total price for each order line item by multiplying unit price and quantity. Shows mathematical operations in SQL.",
        "tables": ["orderdetails"],
        "table_info": {
            "orderdetails": {
                "columns": ["orderid (INT, FK)", "productid (INT, FK)", "unitprice (DECIMAL)", "quantity (INT)", "discount (DECIMAL)"],
                "sample": "orderid: 10248, unitprice: 10.00, quantity: 12 → totalprice: 120.00"
            }
        },
        "solution":"SELECT orderid, productid, unitprice, quantity, unitprice * quantity AS totalprice FROM orderdetails ORDER BY orderid, productid"
    },
    {
        "id":14, 
        "question":"How many customers?", 
        "description": "Count the total number of unique customers in the database. A basic aggregation query to understand database size.",
        "tables": ["customers"],
        "table_info": {
            "customers": {
                "columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)", "contactname (VARCHAR)"],
                "sample": "Total customers: 91"
            }
        },
        "solution":"SELECT COUNT(customerid) AS totalcustomers FROM customers"
    },
    {
        "id":15, 
        "question":"When was the first order?", 
        "description": "Find the earliest order date in the system. Uses MIN() aggregate function for temporal analysis.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "orderdate (DATE)"],
                "sample": "First order date: '1996-07-04'"
            }
        },
        "solution":"SELECT MIN(orderdate) AS firstorder FROM orders"
    },
    {
        "id":16, 
        "question":"Countries where there are customers", 
        "description": "Get unique list of all countries with customers. Uses DISTINCT to eliminate duplicates.",
        "tables": ["customers"],
        "table_info": {
            "customers": {
                "columns": ["customerid (VARCHAR, PK)", "country (VARCHAR)"],
                "sample": "Countries: USA, UK, France, Germany, Canada, Brazil, etc."
            }
        },
        "solution":"SELECT DISTINCT country FROM customers"
    },
    {
        "id":17, 
        "question":"Contact titles for customers", 
        "description": "Count customers by contact title and rank them. Shows GROUP BY with aggregation and sorting.",
        "tables": ["customers"],
        "table_info": {
            "customers": {
                "columns": ["customerid (VARCHAR, PK)", "contacttitle (VARCHAR)"],
                "sample": "contacttitle: 'Sales Manager' (count: 25), 'Owner' (count: 19), etc."
            }
        },
        "solution":"SELECT contacttitle, COUNT(contacttitle) AS total FROM customers GROUP BY contacttitle ORDER BY total DESC"
    },
    {
        "id":18, 
        "question":"Products with associated supplier names", 
        "description": "Link products to their suppliers using INNER JOIN. Shows how to combine data from related tables.",
        "tables": ["products", "suppliers"],
        "table_info": {
            "products": {"columns": ["productid (INT, PK)", "productname (VARCHAR)", "supplierid (INT, FK)"]},
            "suppliers": {"columns": ["supplierid (INT, PK)", "companyname (VARCHAR)"]},
            "relationship": "products.supplierid → suppliers.supplierid"
        },
        "solution":"SELECT productid, productname, companyname FROM products INNER JOIN suppliers ON products.supplierid = suppliers.supplierid ORDER BY productid"
    },
    {
        "id":19, 
        "question":"Orders and the Shipper that was used", 
        "description": "Connect orders with shipping companies to see which carrier was used. Demonstrates JOIN with date formatting.",
        "tables": ["orders", "shippers"],
        "table_info": {
            "orders": {"columns": ["orderid (INT, PK)", "orderdate (DATE)", "shipvia (INT, FK)"]},
            "shippers": {"columns": ["shipperid (INT, PK)", "companyname (VARCHAR)"]},
            "relationship": "orders.shipvia → shippers.shipperid"
        },
        "solution":"SELECT orderid, CAST(orderdate AS DATE) AS orderdate, companyname FROM orders INNER JOIN shippers ON orders.shipvia = shippers.shipperid WHERE orderid < 10300 ORDER BY orderid"
    },
    {
        "id":20, 
        "question":"Categories, and the total products in each category", 
        "description": "Count products per category and rank by frequency. Uses JOIN with GROUP BY and aggregation.",
        "tables": ["products", "categories"],
        "table_info": {
            "products": {"columns": ["productid (INT, PK)", "categoryid (INT, FK)"]},
            "categories": {"columns": ["categoryid (INT, PK)", "categoryname (VARCHAR)"]},
            "relationship": "products.categoryid → categories.categoryid"
        },
        "solution":"SELECT categoryname, COUNT(*) AS totalproducts FROM products INNER JOIN categories ON categories.categoryid = products.categoryid GROUP BY categoryname ORDER BY totalproducts DESC"
    },
    {
        "id":21, 
        "question":"Total customers per country/city", 
        "description": "Analyze customer distribution by geography. Uses GROUP BY with multiple columns and sorting.",
        "tables": ["customers"],
        "table_info": {
            "customers": {
                "columns": ["customerid (VARCHAR, PK)", "city (VARCHAR)", "country (VARCHAR)"],
                "sample": "city: 'London', country: 'UK' (count: 4), city: 'Berlin', country: 'Germany' (count: 2)"
            }
        },
        "solution":"SELECT city, country, COUNT(*) AS total FROM customers GROUP BY country, city ORDER BY total DESC"
    },
    {
        "id":22, 
        "question":"Products that need reordering", 
        "description": "Identify low stock products where units in stock fall below reorder level. Critical for inventory management.",
        "tables": ["products"],
        "table_info": {
            "products": {
                "columns": ["productid (INT, PK)", "productname (VARCHAR)", "unitsinstock (INT)", "reorderlevel (INT)"],
                "sample": "productid: 12, unitsinstock: 0, reorderlevel: 30 (needs reordering)"
            }
        },
        "solution":"SELECT productid, productname, unitsinstock, reorderlevel FROM products WHERE unitsinstock < reorderlevel ORDER BY productid"
    },
    {
        "id":23, 
        "question":"Products that need reordering, continued", 
        "description": "Advanced inventory check considering both stock and on-order quantities. Only shows active products (not discontinued).",
        "tables": ["products"],
        "table_info": {
            "products": {
                "columns": ["productid (INT, PK)", "productname (VARCHAR)", "unitsinstock (INT)", "unitsonorder (INT)", "reorderlevel (INT)", "discontinued (BIT)"],
                "sample": "When (unitsinstock + unitsonorder) <= reorderlevel AND discontinued = 0"
            }
        },
        "solution":"SELECT productid, productname, unitsinstock, unitsonorder, reorderlevel, discontinued FROM products WHERE unitsinstock + unitsonorder <= reorderlevel AND discontinued = 0 ORDER BY productid"
    },
    {
        "id":24, 
        "question":"Customer list by region", 
        "description": "Sort customers with region handling. Uses CASE statement to prioritize customers with null regions.",
        "tables": ["customers"],
        "table_info": {
            "customers": {
                "columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)", "region (VARCHAR)"],
                "sample": "Customers with regions first, then those without (NULL values last)"
            }
        },
        "solution":"SELECT customerid, companyname, region FROM customers ORDER BY (CASE WHEN region IS NULL THEN 1 ELSE 0 END), region, customerid"
    },
    {
        "id":25, 
        "question":"High freight charges", 
        "description": "Find top 3 countries with highest average shipping costs. Shows use of TOP clause and GROUP BY.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "shipcountry (VARCHAR)", "freight (DECIMAL)"],
                "sample": "shipcountry: 'Sweden', averagefreight: 205.38"
            }
        },
        "solution":"SELECT TOP 3 shipcountry, AVG(freight) AS averagefreight FROM orders GROUP BY shipcountry ORDER BY averagefreight DESC"
    },
    {
        "id":26, 
        "question":"High freight charges - 2015", 
        "description": "Analyze shipping costs filtered by year. Demonstrates date filtering for temporal analysis.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "shipcountry (VARCHAR)", "freight (DECIMAL)", "orderdate (DATE)"],
                "sample": "Data filtered for orders between 2015-01-01 and 2016-01-01"
            }
        },
        "solution":"SELECT TOP 3 shipcountry, AVG(freight) AS averagefreight FROM orders WHERE orderdate >= '20150101' AND orderdate < '20160101' GROUP BY shipcountry ORDER BY averagefreight DESC"
    },
    {
        "id":27, 
        "question":"High freight charges with between", 
        "description": "Alternative approach using different date format. Shows flexibility in SQL date comparisons.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "shipcountry (VARCHAR)", "freight (DECIMAL)", "orderdate (DATE)"],
                "sample": "Top 3 countries by average freight in a specific year"
            }
        },
        "solution":"SELECT TOP 3 shipcountry, AVG(freight) AS averagefreight FROM orders WHERE orderdate >= '20150101' AND orderdate < '20160101' GROUP BY shipcountry ORDER BY averagefreight DESC"
    },
    {
        "id":28, 
        "question":"High freight charges - last year", 
        "description": "Dynamic date filtering using DATEADD function. Calculates based on most recent order date.",
        "tables": ["orders"],
        "table_info": {
            "orders": {
                "columns": ["orderid (INT, PK)", "shipcountry (VARCHAR)", "freight (DECIMAL)", "orderdate (DATE)"],
                "sample": "Data from the last year relative to the latest order in the system"
            }
        },
        "solution":"SELECT TOP 3 shipcountry, AVG(freight) AS averagefreight FROM orders WHERE orderdate >= DATEADD(year, -1, (SELECT MAX(orderdate) FROM orders)) GROUP BY shipcountry ORDER BY averagefreight DESC"
    },
    {
        "id":29, 
        "question":"Inventory list", 
        "description": "Create comprehensive inventory snapshot with employee and product information. Complex multi-table JOIN.",
        "tables": ["orders", "employees", "orderdetails", "products"],
        "table_info": {
            "orders": {"columns": ["orderid (INT, PK)", "employeeid (INT, FK)"]},
            "employees": {"columns": ["employeeid (INT, PK)", "lastname (VARCHAR)"]},
            "orderdetails": {"columns": ["orderid (INT, FK)", "productid (INT, FK)", "quantity (INT)"]},
            "products": {"columns": ["productid (INT, PK)", "productname (VARCHAR)"]},
            "relationship": "Multiple JOINs connecting all tables"
        },
        "solution":"SELECT orders.employeeid, employees.lastname, orders.orderid, products.productname, orderdetails.quantity FROM orders INNER JOIN employees ON orders.employeeid = employees.employeeid INNER JOIN orderdetails ON orders.orderid = orderdetails.orderid INNER JOIN products ON products.productid = orderdetails.productid ORDER BY orderid, products.productid"
    },
    {
        "id":30, 
        "question":"Customers with no orders", 
        "description": "Find inactive customers who have never placed orders. Uses LEFT JOIN to identify missing matches.",
        "tables": ["customers", "orders"],
        "table_info": {
            "customers": {"columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)"]},
            "orders": {"columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)"]},
            "relationship": "customers.customerid ← orders.customerid (LEFT JOIN)"
        },
        "solution":"SELECT customers.customerid, orders.customerid FROM customers LEFT JOIN orders ON orders.customerid = customers.customerid WHERE orders.customerid IS NULL"
    },
    {
        "id":31, 
        "question":"Customers with no orders for EmployeeID 4", 
        "description": "Find customers who haven't bought from a specific salesman. Shows conditional LEFT JOIN logic.",
        "tables": ["customers", "orders"],
        "table_info": {
            "customers": {"columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)"]},
            "orders": {"columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "employeeid (INT)"]},
            "relationship": "customers.customerid ← orders.customerid WHERE employeeid = 4"
        },
        "solution":"SELECT customers.customerid, orders.customerid FROM customers LEFT JOIN orders ON orders.customerid = customers.customerid AND orders.employeeid = '4' WHERE orders.customerid IS NULL"
    },
    {
        "id":32, 
        "question":"High-value customers", 
        "description": "Identify individual high-value orders in 2016. Uses aggregation with HAVING clause and multiple table joins.",
        "tables": ["customers", "orders", "orderdetails"],
        "table_info": {
            "customers": {"columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)"]},
            "orders": {"columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "orderdate (DATE)"]},
            "orderdetails": {"columns": ["orderid (INT, FK)", "quantity (INT)", "unitprice (DECIMAL)"]},
            "relationship": "Multiple JOINs with aggregation"
        },
        "solution":"SELECT c.customerid, c.companyname, o.orderid, SUM(od.quantity * od.unitprice) AS totalorderamount FROM customers AS c INNER JOIN orders AS o ON o.customerid = c.customerid INNER JOIN orderdetails AS od ON od.orderid = o.orderid WHERE YEAR(o.orderdate) = 2016 GROUP BY c.customerid, c.companyname, o.orderid HAVING SUM(od.quantity * od.unitprice) > '10000' ORDER BY totalorderamount DESC"
    },
    {
        "id":33, 
        "question":"High-value customers - total orders", 
        "description": "Aggregate high-value customers' total spending in 2016. Shows how to sum across multiple orders.",
        "tables": ["customers", "orders", "orderdetails"],
        "table_info": {
            "customers": {"columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)"]},
            "orders": {"columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "orderdate (DATE)"]},
            "orderdetails": {"columns": ["orderid (INT, FK)", "quantity (INT)", "unitprice (DECIMAL)"]},
            "relationship": "Group all orders per customer and sum totals"
        },
        "solution":"SELECT c.customerid, c.companyname, SUM(od.quantity * od.unitprice) AS totalorderamount FROM customers AS c INNER JOIN orders AS o ON o.customerid = c.customerid INNER JOIN orderdetails AS od ON od.orderid = o.orderid WHERE YEAR(o.orderdate) = 2016 GROUP BY c.customerid, c.companyname HAVING SUM(od.quantity * od.unitprice) >= '15000' ORDER BY totalorderamount DESC"
    },
    {
        "id":34, 
        "question":"High-value customers - with discount", 
        "description": "Calculate actual revenue after applying discounts. Shows business logic with discount calculations.",
        "tables": ["customers", "orders", "orderdetails"],
        "table_info": {
            "customers": {"columns": ["customerid (VARCHAR, PK)", "companyname (VARCHAR)"]},
            "orders": {"columns": ["orderid (INT, PK)", "customerid (VARCHAR, FK)", "orderdate (DATE)"]},
            "orderdetails": {"columns": ["orderid (INT, FK)", "quantity (INT)", "unitprice (DECIMAL)", "discount (DECIMAL)"]},
            "relationship": "Calculate: total = SUM(quantity * unitprice * (1 - discount))"
        },
        "solution":"SELECT c.customerid, c.companyname, SUM(od.quantity * od.unitprice) AS totalswithoutdiscount, SUM(od.quantity * od.unitprice * (1 - discount)) AS totalswithdiscount FROM customers AS c JOIN orders AS o ON o.customerid = c.customerid JOIN orderdetails AS od ON o.orderid = od.orderid WHERE orderdate >= '20160101' AND orderdate < '20170101' GROUP BY c.customerid, c.companyname HAVING SUM(od.quantity * od.unitprice * (1 - discount)) > 10000 ORDER BY totalswithdiscount DESC"
    }
]

# ==========================
# Streamlit App
# ==========================
st.set_page_config(
    page_title="SQL Assessment", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to make the layout more condensed
st.markdown("""
    <style>
        /* Reduce margins and padding */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 100%;
        }
        
        /* Reduce spacing between elements */
        div[data-testid="stVerticalBlock"] > div {
            margin-bottom: 0.5rem;
        }
        
        /* Make text area more compact */
        .stTextArea textarea {
            font-size: 13px;
        }
        
        /* Reduce header spacing */
        h1, h2, h3 {
            margin-bottom: 0.5rem;
            margin-top: 0.5rem;
        }
        
        /* Compact buttons */
        .stButton > button {
            width: 100%;
            padding: 0.5rem;
        }
        
        /* Reduce expander padding */
        .streamlit-expanderContent {
            padding: 0.5rem 1rem;
        }
        
        /* Compact metric display */
        .stMetric {
            background-color: transparent;
            padding: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False
if "feedback_correct" not in st.session_state:
    st.session_state.feedback_correct = False
if "feedback_message" not in st.session_state:
    st.session_state.feedback_message = ""
if "user_sql_input" not in st.session_state:
    st.session_state.user_sql_input = ""

st.title("🗄️ SQL Assessment ")

# Student Name and Email input (at the top for tracking) - MANDATORY
st.markdown("**Student Information** (Required)")
col_name, col_email = st.columns(2)
with col_name:
    student_name = st.text_input("Your Name", key="student_name", placeholder="Enter your full name")
with col_email:
    student_email = st.text_input("Your Email", key="student_email", placeholder="Enter your email address")

# Validate mandatory fields
if not student_name or not student_email:
    st.warning("⚠️ Please enter both your name and email to begin the assessment.")
    st.stop()

# Progress bar
progress = min((st.session_state.current_q + 1) / len(QUESTIONS), 1.0)
st.progress(progress)
st.subheader(f"Question {st.session_state.current_q + 1} of {len(QUESTIONS)}")

q = QUESTIONS[st.session_state.current_q]
st.markdown(f"**Question:** {q['question']}")

# Display description and table information
with st.expander("📋 Question Details & Schema"):
    st.markdown(f"**Description:** {q['description']}")
    st.markdown("**Tables Involved:**")
    for table_name, table_data in q['table_info'].items():
        st.markdown(f"- **{table_name}**")
        if isinstance(table_data, dict):
            if 'columns' in table_data:
                st.write(f"  Columns: {', '.join(table_data['columns'])}")
            if 'sample' in table_data:
                st.markdown("  **Sample Data:**")
                # Parse and format sample data as table
                sample_text = table_data['sample']
                if ' → ' in sample_text:
                    # Handle transformations like casting
                    parts = sample_text.split(' → ')
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Input:**")
                        st.code(parts[0].strip())
                    with col2:
                        st.markdown("**Output:**")
                        st.code(parts[1].strip())
                elif ',' in sample_text and ':' in sample_text:
                    # Parse key-value pairs into table format
                    pairs = [p.strip() for p in sample_text.split(',')]
                    table_data_rows = []
                    for pair in pairs:
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            table_data_rows.append({"Column": key.strip(), "Value": value.strip()})
                    if table_data_rows:
                        st.dataframe(table_data_rows, width='stretch', hide_index=True)
                    else:
                        st.write(f"  {sample_text}")
                else:
                    st.write(f"  {sample_text}")
            if 'relationship' in table_data:
                st.write(f"  Relationship: {table_data['relationship']}")
    
    # Show relationship info if available
    if 'relationship' in q['table_info']:
        st.markdown(f"**Relationship:** {q['table_info']['relationship']}")

# Text area for SQL input
user_sql = st.text_area(
    "Enter your SQL query here:", 
    height=120,
    value=st.session_state.user_sql_input,
    key=f"sql_input_{st.session_state.current_q}"
)

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Submit Answer", type="primary"):
        if not user_sql.strip():
            st.warning("Please enter an answer before submitting.")
        else:
            # Normalize & compare
            normalized_candidate = normalize_sql(user_sql)
            normalized_solution = normalize_sql(q["solution"])
            
            correct = normalized_candidate == normalized_solution
            
            # Store answer
            st.session_state.answers.append({
                "question_id": q["id"],
                "question": q["question"],
                "your_answer": user_sql,
                "correct_answer": q["solution"],
                "is_correct": correct
            })
            
            # Show feedback
            st.session_state.show_feedback = True
            st.session_state.feedback_correct = correct
            if correct:
                st.session_state.feedback_message = "✅ Correct!"
            else:
                st.session_state.feedback_message = "❌ Incorrect."

with col2:
    if st.session_state.current_q + 1 < len(QUESTIONS):
        if st.button("Next Question", disabled=not st.session_state.show_feedback):
            st.session_state.current_q += 1
            st.session_state.show_feedback = False
            st.session_state.user_sql_input = ""
            st.rerun()
    else:
        if st.button("Show Results", disabled=not st.session_state.show_feedback):
            st.session_state.show_feedback = False
            st.session_state.current_q = len(QUESTIONS)  # Mark as completed

# Show feedback if available
if st.session_state.show_feedback:
    if st.session_state.feedback_correct:
        st.success(st.session_state.feedback_message)
    else:
        st.error(st.session_state.feedback_message)
        with st.expander("View solution"):
            st.code(q["solution"], language="sql")
            st.markdown("**Explanation:**")
            st.write(f"Your answer: `{st.session_state.answers[-1]['your_answer']}`")

# Show results when all questions are completed
if (st.session_state.current_q >= len(QUESTIONS) or 
    (len(st.session_state.answers) >= len(QUESTIONS) and st.session_state.current_q == len(QUESTIONS) - 1)):
    
    st.success("🎉 You have completed all questions!")
    
    # Show summary
    st.subheader("📊 Your Results Summary")
    total = len(st.session_state.answers)
    correct_count = sum(a["is_correct"] for a in st.session_state.answers)
    score_percentage = (correct_count / total) * 100
    
    st.metric("Score", f"{correct_count}/{total} ({score_percentage:.1f}%)")
    
    # Save submission to CSV
    if student_name and student_email:
        if not os.path.exists("submissions"):
            os.makedirs("submissions")
        
        # Get current submission datetime
        submission_datetime = datetime.now()
        
        # Create submission data
        submission_data = {
            "Name": student_name,
            "Email": student_email,
            "Submitted At": submission_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "Total Questions": total,
            "Correct Answers": correct_count,
            "Score (%)": round(score_percentage, 2)
        }
        
        # Add individual question results
        for i, ans in enumerate(st.session_state.answers):
            submission_data[f"Q{ans['question_id']}_Answer"] = ans['is_correct']
        
        # Save to submissions folder with timestamp
        submission_file = f"submissions/{student_email}_{submission_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
        submission_df = pd.DataFrame([submission_data])
        submission_df.to_csv(submission_file, index=False)
        st.success(f"✅ Your results have been saved! (Submitted: {submission_datetime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Detailed results
    with st.expander("View Detailed Results"):
        for i, ans in enumerate(st.session_state.answers):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Q{ans['question_id']}: {ans['question']}**")
                st.markdown(f"- Your Answer: `{ans['your_answer']}`")
                st.markdown(f"- Correct Answer: `{ans['correct_answer']}`")
            with col2:
                if ans['is_correct']:
                    st.success("✅ Correct")
                else:
                    st.error("❌ Incorrect")
            st.divider()
    
    # Reset button
    if st.button("Restart Assessment"):
        st.session_state.current_q = 0
        st.session_state.answers = []
        st.session_state.show_feedback = False
        st.session_state.user_sql_input = ""
        st.rerun()

# ==========================
# Admin Section - View All Submissions (Password Protected)
# ==========================
st.divider()
st.subheader("� Admin Dashboard")

# Admin password protection
admin_password = "admin123"  # Change this to a secure password
admin_session = st.session_state.get("admin_authenticated", False)

if not admin_session:
    st.warning("⚠️ This section is restricted to administrators only.")
    entered_password = st.text_input("Enter Admin Password:", type="password", key="admin_password_input")
    
    if st.button("Access Admin Dashboard"):
        if entered_password == admin_password:
            st.session_state.admin_authenticated = True
            st.success("✅ Admin access granted!")
            st.rerun()
        else:
            st.error("❌ Incorrect password. Access denied.")
    st.stop()  # Stop execution if not authenticated

# If authenticated, show admin dashboard
st.success("✅ Admin Mode Active")

# Create submissions folder if it doesn't exist
if not os.path.exists("submissions"):
    os.makedirs("submissions")

# Read all submission files
submission_files = [f for f in os.listdir("submissions") if f.endswith('.csv')]

if submission_files:
    st.subheader("📊 All Student Submissions")
    st.info(f"Total submissions: {len(submission_files)}")
    
    # Load all submissions
    all_submissions = []
    for file in submission_files:
        try:
            df = pd.read_csv(f"submissions/{file}")
            all_submissions.append(df)
        except Exception as e:
            st.warning(f"Error reading {file}: {e}")
    
    if all_submissions:
        # Combine all submissions
        combined_df = pd.concat(all_submissions, ignore_index=True)
        
        # Display submissions table
        st.dataframe(combined_df, width='stretch', hide_index=True)
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export as CSV
            csv_data = combined_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"sql_assessment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Export as Excel
            try:
                import openpyxl
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    combined_df.to_excel(writer, index=False, sheet_name='Submissions')
                excel_buffer.seek(0)
                st.download_button(
                    label="📥 Download as Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"sql_assessment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("Install openpyxl to export as Excel: pip install openpyxl")
        
        with col3:
            st.metric("Total Users", len(combined_df))
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        
        with stats_col1:
            st.metric("Total Submissions", len(combined_df))
        
        with stats_col2:
            if 'Submitted At' in combined_df.columns:
                st.metric("Date Range", f"{combined_df['Submitted At'].min()} to {combined_df['Submitted At'].max()}")
        
        with stats_col3:
            st.metric("Unique Users", combined_df['Name'].nunique() if 'Name' in combined_df.columns else 'N/A')
        
else:
    st.info("No submissions yet. Students can complete the assessment to generate reports.")