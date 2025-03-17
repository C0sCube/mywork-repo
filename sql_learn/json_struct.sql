CREATE DATABASE company_db;
USE company_db;


CREATE TABLE amcs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_name VARCHAR(255) UNIQUE
);


CREATE TABLE mutual_funds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    benchmark_index VARCHAR(255),
    main_scheme_name VARCHAR(255),
    mutual_fund_name VARCHAR(255),
    monthly_aaum_date VARCHAR(50),
    monthly_aaum_value VARCHAR(50),
    scheme_launch_date VARCHAR(50),
    min_addl_amt VARCHAR (50),
    min_addl_amt_multiple VARCHAR (50),
    min_amt VARCHAR (50),
    min_amt_multiple VARCHAR (50),
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);


CREATE TABLE fund_managers (
    amc_id INT,
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_scheme_name VARCHAR(100),
    mutual_fund_id INT,
    manager_name VARCHAR(255),
    qualification VARCHAR(255),
    managing_fund_since VARCHAR(50),
    total_exp VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);


CREATE TABLE loads (
    amc_id INT,
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_scheme_name VARCHAR(100),
    mutual_fund_id INT,
    load_type VARCHAR(255),
    load_value TEXT,
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);


CREATE TABLE metrics (
    amc_id INT,
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_scheme_name VARCHAR(100),
    mutual_fund_id INT,
    metric_type VARCHAR(255),
    metric_value VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);

CREATE TABLE transformed_loads(
    amc_id INT,
	id INT AUTO_INCREMENT PRIMARY KEY,
    main_scheme_name VARCHAR(100),
    mutual_fund_id INT,
    entry_load VARCHAR(100),
    exit_load VARCHAR(400),
	FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);

CREATE TABLE transformed_metrics (
    amc_id INT,
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_scheme_name VARCHAR(100),
    mutual_fund_id INT,
    alpha VARCHAR(40),  
    avg_div_yld VARCHAR(40),  
    avg_maturity VARCHAR(40),  
    avg_pb VARCHAR(40),  
    avg_pe VARCHAR(40),  
    beta VARCHAR(40),
    jenson VARCHAR(40),    
    macaulay_duration VARCHAR(40),  
    modified_duration VARCHAR(40),  
    ptr VARCHAR(40),  
    residual_maturity VARCHAR(40),  
    r_squared VARCHAR(40),  
    roe VARCHAR(40),  
    sharpe VARCHAR(40),  
    sortino VARCHAR(40),  
    std_dev VARCHAR(40),  
    ter VARCHAR(40),  
    tracking_error VARCHAR(40),  
    treynor VARCHAR(40),  
    ytm VARCHAR(40),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);

