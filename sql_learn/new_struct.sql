CREATE DATABASE updated_db;
USE updated_db;

CREATE TABLE amcs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_name VARCHAR(255) UNIQUE
);

CREATE TABLE mutual_funds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    amc_name VARCHAR(255),
    entered_time VARCHAR(40),
    amc_for_month VARCHAR(40),
    benchmark_index TEXT,
    main_scheme_name VARCHAR(255),
    mutual_fund_name VARCHAR(255),
    monthly_aaum_date VARCHAR(50),
    monthly_aaum_value TEXT,
    scheme_launch_date TEXT,
    min_addl_amt VARCHAR(50),
    min_addl_amt_multiple VARCHAR(50),
    min_amt VARCHAR(50),
    min_amt_multiple VARCHAR(50),
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);

CREATE TABLE fund_managers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR(100),
    name VARCHAR(255),
    qualification VARCHAR(255),
    managing_fund_since VARCHAR(50),
    total_exp VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE,
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);

CREATE TABLE transformed_loads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR(100),
    entry_load TEXT,
    exit_load TEXT,
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE,
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);

CREATE TABLE transformed_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR(100),
    alpha VARCHAR(40),  
    arithmetic_mean_ratio VARCHAR(40),  
    average_div_yld VARCHAR(40),  
    average_pb VARCHAR(40),  
    average_pe VARCHAR(40),  
    avg_maturity VARCHAR(40),  
    beta VARCHAR(40),  
    correlation_ratio VARCHAR(40),  
    downside_deviation VARCHAR(40),  
    information_ratio VARCHAR(40),  
    macaulay VARCHAR(40),  
    mod_duration VARCHAR(40),  
    port_turnover_ratio VARCHAR(40),  
    r_squared_ratio VARCHAR(40),  
    roe_ratio VARCHAR(40),  
    sharpe VARCHAR(40),  
    sortino_ratio VARCHAR(40),  
    std_dev VARCHAR(40),
    tracking_error VARCHAR(40),  
    treynor_ratio VARCHAR(40),  
    upside_deviation VARCHAR(40),  
    ytm VARCHAR(40),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE,
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);


SELECT * FROM transformed_loads;

SELECT * FROM amcs;

SELECT * FROM transformed_metrics;

SELECT * FROM fund_managers;

SELECT * FROM mutual_funds;

    

SELECT mf.mutual_fund_name, GROUP_CONCAT(fm.name SEPARATOR ', ') AS fund_managers
FROM fund_managers fm
JOIN mutual_funds mf ON fm.mutual_fund_id = mf.id
GROUP BY mf.mutual_fund_name;


SELECT 
    mf.*,  
    fm.name AS fund_manager_name, fm.qualification, fm.managing_fund_since, fm.total_exp,
    tl.entry_load, tl.exit_load,
    tm.*  
FROM mutual_funds mf
LEFT JOIN fund_managers fm ON mf.id = fm.mutual_fund_id
LEFT JOIN transformed_loads tl ON mf.id = tl.mutual_fund_id
LEFT JOIN transformed_metrics tm ON mf.id = tm.mutual_fund_id;

-- INSERT INTO amcs (amc_name) VALUES
-- ("360 ONE Mutual Fund"),
-- ("Aditya Birla Sun Life Mutual Fund"),
-- ("Axis Mutual Fund"),
-- ("Bajaj finserv Mutual Fund"),
-- ("Bandhan Mutual Fund"),
-- ("Bank of India Mutual Fund"),
-- ("Baroda BNP Paribas Mutual Fund"),
-- ("Canara Robeco Mutual Fund"),
-- ("DSP Mutual Fund"),
-- ("Edelweiss Mutual Fund"),
-- ("Franklin Templeton Mutual Fund"),
-- ("Groww Mutual Fund"),
-- ("Helios Mutual Fund"),
-- ("HSBC Mutual Fund"),
-- ("ICICI Prudential Mutual Fund"),
-- ("Invesco Mutual Fund"),
-- ("ITI Mutual Fund"),
-- ("JM Financial Mutual Fund"),
-- ("Kotak Mahindra Mutual Fund"),
-- ("LIC Mutual Fund"),
-- ("Mahindra Manulife Mutual Fund"),
-- ("Mirae Asset Mutual Fund"),
-- ("Motilal Oswal Mutual Fund"),
-- ("Navi Mutual Fund"),
-- ("Nippon India Mutual Fund"),
-- ("NJ Mutual Fund"),
-- ("Old Bridge Mutual Fund"),
-- ("PGIM India Mutual Fund"),
-- ("PPFAS Mutual Fund"),
-- ("Quant Mutual Fund"),
-- ("Quantum Mutual Fund"),
-- ("Samco Mutual Fund"),
-- ("SBI Mutual Fund"),
-- ("Shriram Mutual fund"),
-- ("Sundaram Mutual Fund"),
-- ("Tata Mutual Fund"),
-- ("Taurus Mutual Fund"),
-- ("Trust Mutual Fund"),
-- ("Union Mutual Fund"),
-- ("UTI Mutual Fund"),
-- ("WhiteOak Mutual Fund"),
-- ("Zerodha Mutual Fund");

