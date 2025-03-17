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
    FOREIGN KEY (amc_id) REFERENCES amcs(id) ON DELETE CASCADE
);


CREATE TABLE fund_managers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    manager_name VARCHAR(255),
    qualification VARCHAR(255),
    managing_fund_since VARCHAR(50),
    total_exp VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);


CREATE TABLE loads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    load_type VARCHAR(255),
    load_value TEXT,
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);


CREATE TABLE metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    name VARCHAR(255),
    value VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);


CREATE TABLE fund_minimum_amounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    amt VARCHAR(50),
    thraftr VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);


CREATE TABLE fund_additional_amounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mutual_fund_id INT,
    amt VARCHAR(50),
    thraftr VARCHAR(50),
    FOREIGN KEY (mutual_fund_id) REFERENCES mutual_funds(id) ON DELETE CASCADE
);
