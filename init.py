import sqlite3

DB_NAME = "itembase.db"

def create_database():
    connection = sqlite3.connect(DB_NAME)

    connection.execute("PRAGMA foreign_keys = ON;")

    cursor = connection.cursor()

    cursor.executescript(
        #items
        """CREATE TABLE IF NOT EXISTS items 
        (
            iid INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT CHECK(type IN ('fridge', 'hire', 'physical', 'shuttles')) NOT NULL,
            name TEXT NOT NULL,
            price INTEGER
        );"""       
        #stringing
        """ CREATE TABLE IF NOT EXISTS stringing
        (
            sid INTEGER PRIMARY KEY,
            string_type TEXT NOT NULL,
            string_price INTEGER,
            member_price INTEGER
        );"""
         #users
        """ CREATE TABLE IF NOT EXISTS users
        (
            uid INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        );"""
        #custom orders
        """ CREATE TABLE IF NOT EXISTS custom_orders
        (
            coid INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            price INTEGER
        );"""
        #walk ins
        """CREATE TABLE IF NOT EXISTS walk_ins
        (
            peak_offpeak BIT NOT NULL,
            price INTEGER,
            member_price INTEGER
        );"""
        #checkout
        """ CREATE TABLE IF NOT EXISTS checkout
        (
            checkout_date TEXT NOT NULL,
            total_price INTEGER NOT NULL,
            cash_card BIT NOT NULL,
            iid INTEGER,
            discount INTEGER,
            user TEXT NOT NULL,
            FOREIGN KEY(iid) REFERENCES items(iid)
        );"""
    )
    
    

    connection.commit()

    connection.close()

    print("Database created successfully.")# this statement is a saftey feature the will only execute if this file
# is run directly. So if you import this file into another project it
# won't accidentally run
if __name__ == "__main__":
    create_database()
    