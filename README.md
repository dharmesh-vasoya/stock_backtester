install mysql

open console
mysql -u root -p

select db
use database_name

create db with database_name

Create the table with required fields
CREATE TABLE backtest_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock VARCHAR(50) NOT NULL,
    buy_price FLOAT NOT NULL,
    sell_price FLOAT,
    buy_time_human VARCHAR(50),
    buy_time_epoch INT,
    sell_time_human VARCHAR(50),
    sell_time_epoch INT,
    pnl FLOAT
);

Grafana query to create table

Add sql data source and then enter below query in console creator

SELECT 
    stock,
    buy_price,
    buy_time_human AS buy_time,
    sell_price,
    sell_time_human AS sell_time,
    pnl
FROM 
    backtest_data;

Show the list of tables:
SHOW TABLES;

to see table content
SELECT * FROM backtest_data;


to delete old data

-- Step 1: Drop the existing table if it exists

select db 
use database_name

to delete
DROP TABLE IF EXISTS backtest_data;



