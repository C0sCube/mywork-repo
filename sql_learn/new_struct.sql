CREATE DATABASE try_db;
USE try_db;

CREATE TABLE amcs
(
    id INT
    AUTO_INCREMENT PRIMARY KEY,
    amc_name VARCHAR
    (255) UNIQUE
);

    CREATE TABLE mutual_funds
    (
        id INT
        AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    amc_name VARCHAR
        (255),
    entered_time VARCHAR
        (40),
    amc_for_month VARCHAR
        (40),
    data_from VARCHAR
        (100),
    benchmark_index TEXT,
    main_scheme_name TEXT,
    mutual_fund_name TEXT,
    monthly_aaum_date VARCHAR
        (50),
    monthly_aaum_value TEXT,
    scheme_launch_date TEXT,
    min_addl_amt VARCHAR
        (50),
    min_addl_amt_multiple VARCHAR
        (50),
    min_amt VARCHAR
        (50),
    min_amt_multiple VARCHAR
        (50),
    FOREIGN KEY
        (amc_id) REFERENCES amcs
        (id) ON
        DELETE CASCADE
);

        CREATE TABLE fund_managers
        (
            id INT
            AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR
            (100),
    name VARCHAR
            (255),
    qualification VARCHAR
            (255),
    managing_fund_since VARCHAR
            (50),
    total_exp VARCHAR
            (50),
    FOREIGN KEY
            (mutual_fund_id) REFERENCES mutual_funds
            (id) ON
            DELETE CASCADE,
    FOREIGN KEY (amc_id)
            REFERENCES amcs
            (id) ON
            DELETE CASCADE
);

            CREATE TABLE transformed_loads
            (
                id INT
                AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR
                (100),
    entry_load TEXT,
    exit_load TEXT,
    FOREIGN KEY
                (mutual_fund_id) REFERENCES mutual_funds
                (id) ON
                DELETE CASCADE,
    FOREIGN KEY (amc_id)
                REFERENCES amcs
                (id) ON
                DELETE CASCADE
);

                CREATE TABLE transformed_metrics
                (
                    id INT
                    AUTO_INCREMENT PRIMARY KEY,
    amc_id INT,
    mutual_fund_id INT,
    main_scheme_name VARCHAR
                    (100),
    alpha VARCHAR
                    (40),  
    arithmetic_mean_ratio VARCHAR
                    (40),  
    average_div_yld VARCHAR
                    (40),  
    average_pb VARCHAR
                    (40),  
    average_pe VARCHAR
                    (40),  
    avg_maturity VARCHAR
                    (40),  
    beta VARCHAR
                    (40),  
    correlation_ratio VARCHAR
                    (40),  
    downside_deviation VARCHAR
                    (40),  
    information_ratio VARCHAR
                    (40),  
    macaulay VARCHAR
                    (40),  
    mod_duration VARCHAR
                    (40),  
    port_turnover_ratio VARCHAR
                    (40),  
    r_squared_ratio VARCHAR
                    (40),  
    roe_ratio VARCHAR
                    (40),  
    sharpe VARCHAR
                    (40),  
    sortino_ratio VARCHAR
                    (40),  
    std_dev VARCHAR
                    (40),
    tracking_error VARCHAR
                    (40),  
    treynor_ratio VARCHAR
                    (40),  
    upside_deviation VARCHAR
                    (40),  
    ytm VARCHAR
                    (40),
    FOREIGN KEY
                    (mutual_fund_id) REFERENCES mutual_funds
                    (id) ON
                    DELETE CASCADE,
    FOREIGN KEY (amc_id)
                    REFERENCES amcs
                    (id) ON
                    DELETE CASCADE
);

                    ALTER TABLE mutual_funds ADD COLUMN data_from VARCHAR
                    (100);




'mf_json_fund_managers', 'CREATE TABLE `mf_json_fund_managers` (\n  `id` int(11) NOT NULL AUTO_INCREMENT,\n  `document_detail_id` int(11) DEFAULT NULL,\n  `MainScheme_ID` int(11) DEFAULT NULL,\n  `main_scheme_name` varchar(500) DEFAULT NULL,\n  `name` varchar(100) DEFAULT NULL,\n  `managing_fund_since` varchar(100) DEFAULT NULL,\n  `qualification` varchar(1000) DEFAULT NULL,\n  `total_experience` varchar(1000) DEFAULT NULL,\n  `entered_user` varchar(100) DEFAULT NULL,\n  `entered_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,\n  `modified_user` varchar(100) DEFAULT NULL,\n  `modified_date` timestamp NULL DEFAULT NULL,\n  `is_migrated` tinyint(4) DEFAULT NULL,\n  PRIMARY KEY (`id`),\n  UNIQUE KEY `uc_mf_json_fund_managers` (`document_detail_id`,`main_scheme_name`,`name`,`managing_fund_since`,`qualification`,`total_experience`,`is_migrated`),\n  KEY `fk_mf_json_fund_managers_document_detail_id_idx` (`document_detail_id`),\n  KEY `fk_mf_json_fund_managers_main_scheme_id_idx` (`MainScheme_ID`),\n  CONSTRAINT `fk_mf_json_fund_managers_document_detail_id` FOREIGN KEY (`document_detail_id`) REFERENCES `mf_document_details` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION,\n  CONSTRAINT `fk_mf_json_fund_managers_main_scheme_id` FOREIGN KEY (`MainScheme_ID`) REFERENCES `mf_master_mainscheme` (`MainScheme_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION\n) ENGINE=InnoDB AUTO_INCREMENT=97106 DEFAULT CHARSET=latin1'
'mf_json_asset_allocation_patterns', 'CREATE TABLE `mf_json_asset_allocation_patterns` (\n  `id` int(11) NOT NULL AUTO_INCREMENT,\n  `document_detail_id` int(11) DEFAULT NULL,\n  `MainScheme_ID` int(11) DEFAULT NULL,\n  `main_scheme_name` varchar(500) DEFAULT NULL,\n  `instrument_type` varchar(500) DEFAULT NULL,\n  `risk_level_id` int(11) DEFAULT NULL,\n  `risk_level` varchar(100) DEFAULT NULL,\n  `min` varchar(50) DEFAULT NULL,\n  `max` varchar(50) DEFAULT NULL,\n  `total` varchar(50) DEFAULT NULL,\n  `entered_user` varchar(100) DEFAULT NULL,\n  `entered_date` datetime DEFAULT CURRENT_TIMESTAMP,\n  `modified_user` varchar(100) DEFAULT NULL,\n  `modified_date` timestamp NULL DEFAULT NULL,\n  `is_migrated` tinyint(4) DEFAULT NULL,\n  PRIMARY KEY (`id`),\n  UNIQUE KEY `uc_mf_json_asset_allocation_patterns` (`document_detail_id`,`main_scheme_name`,`instrument_type`,`risk_level`,`is_migrated`),\n  KEY `mf_json_asset_allocation_patterns_document_detail_id_idx` (`document_detail_id`),\n  KEY `fk_mf_json_asset_allocation_patterns_main_scheme_id_idx` (`MainScheme_ID`),\n  CONSTRAINT `fk_mf_json_asset_allocation_patterns_document_detail_id` FOREIGN KEY (`document_detail_id`) REFERENCES `mf_document_details` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION,\n  CONSTRAINT `fk_mf_json_asset_allocation_patterns_main_scheme_id` FOREIGN KEY (`MainScheme_ID`) REFERENCES `mf_master_mainscheme` (`MainScheme_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION\n) ENGINE=InnoDB AUTO_INCREMENT=804 DEFAULT CHARSET=latin1'
'mf_json_loads', 'CREATE TABLE `mf_json_loads` (\n  `id` int(11) NOT NULL AUTO_INCREMENT,\n  `document_detail_id` int(11) DEFAULT NULL,\n  `MainScheme_ID` int(11) DEFAULT NULL,\n  `main_scheme_name` varchar(500) DEFAULT NULL,\n  `comment` varchar(5000) DEFAULT NULL,\n  `load_type_id` int(11) DEFAULT NULL,\n  `type` varchar(500) DEFAULT NULL,\n  `value` varchar(500) DEFAULT NULL,\n  `entered_user` varchar(100) DEFAULT NULL,\n  `entered_date` datetime DEFAULT CURRENT_TIMESTAMP,\n  `modified_user` varchar(100) DEFAULT NULL,\n  `modified_date` timestamp NULL DEFAULT NULL,\n  `is_migrated` varchar(45) DEFAULT NULL,\n  PRIMARY KEY (`id`),\n  UNIQUE KEY `uc_mf_json_loads` (`document_detail_id`,`main_scheme_name`,`type`,`value`,`is_migrated`),\n  KEY `fk_mf_json_loads_document_detail_id_idx` (`document_detail_id`),\n  KEY `fk_mf_json_loads_main_scheme_id_idx` (`MainScheme_ID`),\n  KEY `fk_mf_json_loads_load_type_id_idx` (`load_type_id`),\n  CONSTRAINT `fk_mf_json_loads_document_detail_id` FOREIGN KEY (`document_detail_id`) REFERENCES `mf_document_details` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION,\n  CONSTRAINT `fk_mf_json_loads_load_type_id` FOREIGN KEY (`load_type_id`) REFERENCES `mf_master_loadtype` (`LoadType_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,\n  CONSTRAINT `fk_mf_json_loads_main_scheme_id` FOREIGN KEY (`MainScheme_ID`) REFERENCES `mf_master_mainscheme` (`MainScheme_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION\n) ENGINE=InnoDB AUTO_INCREMENT=74606 DEFAULT CHARSET=latin1'
'mf_json_benchmark_indices', 'CREATE TABLE `mf_json_benchmark_indices` (\n  `id` int(11) NOT NULL AUTO_INCREMENT,\n  `document_detail_id` int(11) DEFAULT NULL,\n  `MainScheme_ID` int(11) DEFAULT NULL,\n  `main_scheme_name` varchar(500) DEFAULT NULL,\n  `benchmark_index_id` int(11) DEFAULT NULL,\n  `benchmark_index` varchar(1000) DEFAULT NULL,\n  `entered_user` varchar(100) DEFAULT NULL,\n  `entered_date` datetime DEFAULT CURRENT_TIMESTAMP,\n  `modified_user` varchar(100) DEFAULT NULL,\n  `modified_date` timestamp NULL DEFAULT NULL,\n  `is_migrated` varchar(45) DEFAULT NULL,\n  `riskometer_benchmark` varchar(100) DEFAULT NULL,\n  PRIMARY KEY (`id`),\n  UNIQUE KEY `ui_mf_json_benchmark_indices` (`document_detail_id`,`main_scheme_name`,`benchmark_index`,`is_migrated`),\n  KEY `fk_mf_json_benchmark_indices_document_detail_id_idx` (`document_detail_id`),\n  KEY `fk_mf_json_benchmark_indices_main_scheme_id_idx` (`MainScheme_ID`),\n  CONSTRAINT `fk_mf_json_benchmark_indices_document_detail_id` FOREIGN KEY (`document_detail_id`) REFERENCES `mf_document_details` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION,\n  CONSTRAINT `fk_mf_json_benchmark_indices_main_scheme_id` FOREIGN KEY (`MainScheme_ID`) REFERENCES `mf_master_mainscheme` (`MainScheme_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION\n) ENGINE=InnoDB AUTO_INCREMENT=56704 DEFAULT CHARSET=latin1'
'mf_json_field_locations', 'CREATE TABLE `mf_json_field_locations` (\n  `id` int(11) NOT NULL AUTO_INCREMENT,\n  `document_detail_id` int(11) DEFAULT NULL,\n  `MainScheme_ID` int(11) DEFAULT NULL,\n  `main_scheme_name` varchar(500) DEFAULT NULL,\n  `field_name` varchar(100) DEFAULT NULL,\n  `page_no` int(11) DEFAULT NULL,\n  `entered_user` varchar(100) DEFAULT NULL,\n  `entered_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,\n  `modified_user` varchar(100) DEFAULT NULL,\n  `modified_date` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,\n  `is_migrated` tinyint(4) DEFAULT NULL,\n  PRIMARY KEY (`id`),\n  UNIQUE KEY `uc_mf_json_field_locations` (`document_detail_id`,`main_scheme_name`,`field_name`,`page_no`,`is_migrated`),\n  KEY `fk_mf_json_field_locations_document_detail_id_idx` (`document_detail_id`),\n  KEY `fk_mf_json_field_locations_main_scheme_id_idx` (`MainScheme_ID`),\n  CONSTRAINT `fk_mf_json_field_locations_main_scheme_id` FOREIGN KEY (`MainScheme_ID`) REFERENCES `mf_master_mainscheme` (`MainScheme_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION\n) ENGINE=InnoDB AUTO_INCREMENT=866300 DEFAULT CHARSET=latin1'

