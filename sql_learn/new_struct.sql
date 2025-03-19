CREATE DATABASE updated_db;
USE updated_db;

-- amc table
CREATE TABLE amcs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_name VARCHAR(255) UNIQUE
);

-- grand table
CREATE TABLE mutual_funds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    amc_name VARCHAR(255),
    entered_time VARCHAR(40),
    amc_for_month VARCHAR(40),
    benchmark_index VARCHAR(255),
    main_scheme_name VARCHAR(255),
    mutual_fund_name VARCHAR(255),
    monthly_aaum_date VARCHAR(50),
    monthly_aaum_value VARCHAR(50),
    scheme_launch_date VARCHAR(50),
    min_addl_amt VARCHAR(50),
    min_addl_amt_multiple VARCHAR(50),
    min_amt VARCHAR(50),
    min_amt_multiple VARCHAR(50),
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);

-- managers
CREATE TABLE fund_managers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR(100),
    name VARCHAR(255),
    qualification VARCHAR(255),
    managing_fund_since VARCHAR(50),
    total_exp VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);

-- loads
CREATE TABLE transformed_loads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR(100),
    entry_load VARCHAR(100),
    exit_load TEXT,
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);

-- metrics
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
	treynor_ratio VARCHAR(40),  
	upside_deviation VARCHAR(40),  
	ytm VARCHAR(40),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);
