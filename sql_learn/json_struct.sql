CREATE DATABASE company_db;
USE company_db;

CREATE TABLE mutual_funds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amc_name VARCHAR(255),
    main_scheme_name VARCHAR(255),
    min_amt VARCHAR(50),
    min_addl_amt VARCHAR(50),
    min_amt_multiple VARCHAR(50),
    min_addl_amt_multiple VARCHAR(50),
    monthly_aaum_date VARCHAR(50),
    monthly_aaum_value VARCHAR(50),
    scheme_launch_date VARCHAR(50),
    mutual_fund_name VARCHAR(255)
);

CREATE TABLE fund_managers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    name VARCHAR(255),
    managing_fund_since VARCHAR(50),
    total_exp VARCHAR(50),
    qualification TEXT,
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id)
);

CREATE TABLE loads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    type ENUM('entry', 'exit'),
    comment TEXT,
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id)
);

CREATE TABLE metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    name VARCHAR(255),
    value VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id)
);

CREATE TABLE benchmark_index (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    index_name VARCHAR(255),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id)
);
