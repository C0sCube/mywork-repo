CREATE DATABASE FundHouseDB;
USE FundHouseDB;

CREATE TABLE fund_houses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE params (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    line_x FLOAT,
    method VARCHAR(50),
    line_side VARCHAR(50),
    max_financial_index_highlight INT,
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE fund_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    flag JSON,
    regex VARCHAR(255),
    size JSON,
    color JSON,
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE data_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    size JSON,
    color JSON,
    update_size FLOAT,
    font JSON,
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE regex_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    key_name VARCHAR(255),
    pattern TEXT,
    is_list BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE regex_list_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    regex_pattern_id INT,
    item TEXT,
    FOREIGN KEY (regex_pattern_id) REFERENCES regex_patterns(id) ON DELETE CASCADE
);

CREATE TABLE pattern_to_function (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    pattern VARCHAR(255),
    function_name VARCHAR(255),
    param VARCHAR(255),
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE select_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    key_value VARCHAR(255),
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE merge_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    key_value VARCHAR(255),
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);

CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_house_id INT,
    comment TEXT,
    FOREIGN KEY (fund_house_id) REFERENCES fund_houses(id) ON DELETE CASCADE
);
