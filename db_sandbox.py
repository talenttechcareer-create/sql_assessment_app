import sqlite3

def create_sandbox():
    """
    Creates an in-memory SQLite database with sample tables:
    - CITY
    - tweets
    - departments
    - employees

    Returns:
        conn: sqlite3.Connection object
    """
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # ----------------------
    # Create tables
    # ----------------------
    cur.execute("""
    CREATE TABLE CITY(
        id INTEGER PRIMARY KEY,
        name TEXT,
        countrycode TEXT,
        population INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE tweets(
        tweet_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        msg TEXT,
        tweet_date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE departments(
        id INTEGER PRIMARY KEY,
        dept_name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE employees(
        id INTEGER PRIMARY KEY,
        name TEXT,
        dept_id INTEGER,
        salary REAL,
        FOREIGN KEY(dept_id) REFERENCES departments(id)
    )
    """)

    # ----------------------
    # Insert sample data
    # ----------------------
    # CITY
    city_data = [
        (1, "Tokyo", "JPN", 13929286),
        (2, "Yokohama", "JPN", 3726167),
        (3, "New York", "USA", 8419600),
        (4, "Los Angeles", "USA", 3980400),
        (5, "Paris", "FRA", 2148000)
    ]
    cur.executemany("INSERT INTO CITY VALUES (?,?,?,?)", city_data)

    # tweets
    tweets_data = [
        (214252, 111, "Message1", "2021-12-30"),
        (739252, 111, "Message2", "2022-01-01"),
        (846402, 111, "Message3", "2022-02-14"),
        (241425, 254, "Message4", "2022-03-01"),
        (231574, 148, "Message5", "2022-03-23")
    ]
    cur.executemany("INSERT INTO tweets VALUES (?,?,?,?)", tweets_data)

    # departments
    departments_data_
