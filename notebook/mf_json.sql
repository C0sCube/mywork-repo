CREATE DEFINER=`cog_mf`@`%` PROCEDURE `mf_processjson_factsheet`(p1 MEDIUMTEXT)
BEGIN

-- read meta data 
SET @document_name = replace(JSON_UNQUOTE(JSON_EXTRACT(p1,'$.metadata.document_name')),'.pdf','.json') ;
SET @document_id = (SELECT id FROM mf_document_details 
					WHERE doc_type='FS' AND fund_id = SplitString(@document_name,"_",1) 
                    and filename = @document_name
					AND asondate = STR_TO_DATE(SplitString(@document_name,"_", 2), '%e-%b-%Y'));

SET @process_date = JSON_UNQUOTE(JSON_EXTRACT(p1,'$.metadata.process_date'));
-- update process date in document detail table
UPDATE `mf_document_details` 
SET  `processdate` = STR_TO_DATE(@process_date, '%Y%m%d'),  `modified_user` = 'auto', `modified_date` = now()  WHERE `id` = @document_id;


SET @indx = 0;
SET @records	=	JSON_EXTRACT(p1, '$.records');
IF JSON_LENGTH(@records) >0 
THEN 
REPEAT       
        SET @schemeData			=	JSON_EXTRACT(@records, CONCAT("$[", @indx, "]"));
        SET @amc_name			=	trim(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.amc_name')));
		SET @mutual_fund_name	=	trim(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.mutual_fund_name')));
		SET @main_scheme_name	=	trim(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.main_scheme_name')));
		SET @scheme_launch_date	=	JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.scheme_launch_date'));        
        SET @MainScheme_ID 		= 	(SELECT MainScheme_ID from mf_master_mainscheme where mainschemename = cast(@main_scheme_name as char));
        
        SET @min_addl_amt			=	trim(replace(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.min_addl_amt')),'?',''));
		SET @min_addl_amt_multiple	=	trim(replace(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.min_addl_amt_multiple')),'?',''));
		SET @min_amt				=	trim(replace(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.min_amt')),'?',''));
        SET @min_amt_multiple		=	trim(replace(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.min_amt_multiple')),'?',''));
		SET @monthly_aaum_date		=	JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.monthly_aaum_date'));
        SET @monthly_aaum_value		=	trim(replace(JSON_UNQUOTE(JSON_EXTRACT(@schemeData, '$.value.monthly_aaum_value')),'?',''));
        
        SET @matrics 				= 	JSON_EXTRACT(@schemeData, '$.value.metrics');
        SET @ytm	    			=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','ytm',NULL, '$[*].name')),'.name','.value')));
        SET @port_turnover_ratio	=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','port_turnover_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @mod_duration	    	=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','mod_duration',NULL, '$[*].name')),'.name','.value')));
        SET @avg_maturity	    	=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','avg_maturity',NULL, '$[*].name')),'.name','.value')));
        SET @macaulay	    		=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','macaulay',NULL, '$[*].name')),'.name','.value')));
        SET @sharpe	    			=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','sharpe',NULL, '$[*].name')),'.name','.value')));
        SET @std_dev	    		=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','std_dev',NULL, '$[*].name')),'.name','.value')));
        SET @beta	    			=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','beta',NULL, '$[*].name')),'.name','.value')));
		SET @tracking_error			=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','tracking_error',NULL, '$[*].name')),'.name','.value')));
        SET @r_squared_ratio		=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','r_squared_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @average_div_yield		=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','average_div_yield',NULL, '$[*].name')),'.name','.value')));
        SET @average_pb				=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','average_pb',NULL, '$[*].name')),'.name','.value')));
        SET @average_pe				=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','average_pe',NULL, '$[*].name')),'.name','.value')));
        SET @treynor_ratio			=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','treynor_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @alpha					=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','alpha',NULL, '$[*].name')),'.name','.value')));
        SET @information_ratio		=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','information_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @sortino_ratio		    =  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','sortino_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @arithmetic_mean_ratio	=  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','arithmetic_mean_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @correlation_ratio	    =  	JSON_UNQUOTE(JSON_EXTRACT(@matrics,Replace(JSON_UNQUOTE(JSON_SEARCH(@matrics,'one','correlation_ratio',NULL, '$[*].name')),'.name','.value')));
        SET @system_user_id			= 	'auto';
        SET @amc_id 				=	(select amc_id from mf_master_amc where AMC_LongName =cast(@amc_name as char));
		SET @fund_id				=	(select fund_id from mf_master_fund where longname = cast(@mutual_fund_name as char));

       IF EXISTS ( SELECT 1 FROM `mf_json_common_details` WHERE `document_detail_id` = @document_id
													AND `amc_name` = @amc_name
													AND `main_scheme_name` = @main_scheme_name
													AND `fund_name` = @mutual_fund_name
													AND `is_migrated` = false) THEN		
			UPDATE `mf_json_common_details`
				SET `min_addl_amt` = @min_addl_amt,
					`min_addl_amt_multiple` = @min_addl_amt_multiple,
					`min_amt` = @min_amt,
					`min_amt_multiple` = @min_amt_multiple,
					`monthly_aaum_date` = @monthly_aaum_date,
					`monthly_aaum_value` = @monthly_aaum_value,
					`scheme_launch_date` = @scheme_launch_date,
					`ytm` = @ytm,
					`port_turnover_ratio` = @port_turnover_ratio,
					`mod_duration` = @mod_duration,
					`avg_maturity` = @avg_maturity,
					`macaulay` = @macaulay,
					`sharpe` = @sharpe,
					`beta` = @beta,
					`r_squared_ratio` = @r_squared_ratio,
					`average_div_yield` = @average_div_yield,
					`average_pb` = @average_pb,
					`average_pe` = @average_pe,
					`tracking_error` = @tracking_error,
					`treynor_ratio` = @treynor_ratio,
					`alpha` = @alpha,
                    `information_ratio`=@information_ratio,
                    `sortino_ratio`=@sortino_ratio,
                     `arithmetic_mean_ratio`=@arithmetic_mean_ratio,
                     `correlation_ratio`=@correlation_ratio
				WHERE `document_detail_id` = @document_id
				  AND `amc_name` = @amc_name
				  AND `main_scheme_name` = @main_scheme_name
				  AND `fund_name` = @mutual_fund_name
				  AND `is_migrated` = false;

        ELSE
        
			 INSERT INTO `mf_json_common_details`
					(`document_detail_id`,`amc_id`,`amc_name`,`MainScheme_ID`,`main_scheme_name`,`fund_id`,`fund_name`,`min_addl_amt`,
                    `min_addl_amt_multiple`,`min_amt`,`min_amt_multiple`,`monthly_aaum_date`,`monthly_aaum_value`,`scheme_launch_date`,
					`ytm`,`port_turnover_ratio`,`mod_duration`,`avg_maturity`,`macaulay`,`sharpe`,`std_dev`,`beta`,
                    `r_squared_ratio`,`average_div_yield`,`average_pb`,`average_pe`,`tracking_error`,`treynor_ratio`,`alpha`, `information_ratio`,`sortino_ratio`,`arithmetic_mean_ratio`,`correlation_ratio`,`entered_user`,`is_migrated`)
			VALUES	(@document_id, @amc_id, @amc_name, @MainScheme_ID, @main_scheme_name, @fund_id, @mutual_fund_name, @min_addl_amt, 
					 @min_addl_amt_multiple, @min_amt, @min_amt_multiple, @monthly_aaum_date, @monthly_aaum_value, @scheme_launch_date,
                     @ytm, @port_turnover_ratio, @mod_duration, @avg_maturity, @macaulay, @sharpe, @std_dev, 
                     @beta,@r_squared_ratio, @average_div_yield, @average_pb,@average_pe,@tracking_error, @treynor_ratio,@alpha, @information_ratio,@sortino_ratio,@arithmetic_mean_ratio,@correlation_ratio, @system_user_id,false);
        
        END IF;
        
     SET @indxBI = 0;
     SET @benchmark_index = JSON_EXTRACT(@schemeData,'$.value.benchmark_index');
     IF JSON_LENGTH (@benchmark_index) > 0
     THEN
		REPEAT
			SET @benchmark_index_name = trim(JSON_UNQUOTE (JSON_EXTRACT(@benchmark_index, CONCAT("$[", @indxBI, "]")))); 
			SET @benchmark_index_id	= 	(select id from mf_master_index where index_name = Cast(@benchmark_index_name as CHAR));       
            
			INSERT INTO `mf_json_benchmark_indices`
						(`document_detail_id`,`MainScheme_ID`,`main_scheme_name`,`benchmark_index_id`,`benchmark_index`,`entered_user`,`entered_date`,`is_migrated`)
				VALUES	(@document_id, @MainScheme_ID, @main_scheme_name, @benchmark_index_id, @benchmark_index_name, @system_user_id,now(),0)
                ON DUPLICATE KEY UPDATE	MainScheme_ID = @MainScheme_ID,
										main_scheme_name = @main_scheme_name,
                                        benchmark_index_id = @benchmark_index_id,
                                        benchmark_index = @benchmark_index_name;
        
        SET @indxBI = @indxBI + 1;        
        UNTIL @indxBI = JSON_LENGTH (@benchmark_index)
		END REPEAT;
	 END IF;
		
        
	-- insert field location details
	SET @indxFL = 0;
	SET @fieldLocations = JSON_KEYS(JSON_EXTRACT(@schemeData,'$.value.field_location[0]'));   
	IF JSON_LENGTH (@fieldLocations) >0 
		THEN 
			REPEAT	
				SET @fieldName = JSON_EXTRACT(@fieldLocations, CONCAT("$[", @indxFL, "]"));   
				SET @fieldValue = JSON_UNQUOTE(JSON_EXTRACT(@schemeData, CONCAT('$.value.field_location[0].',@fieldName)));
    
					INSERT INTO `mf_json_field_locations` 
						(`document_detail_id`,`MainScheme_ID`,`main_scheme_name`,`field_name`,`page_no`,`entered_user`,`is_migrated`)
			SELECT * FROM (SELECT @document_id, @MainScheme_ID,@main_scheme_name, JSON_UNQUOTE(@fieldName),@fieldValue,@system_user_id,false)AS tmp
			WHERE NOT EXISTS (
								SELECT document_detail_id FROM mf_json_field_locations WHERE document_detail_id = @document_id and main_scheme_name = @main_scheme_name 
                                and is_migrated= false and field_name = JSON_UNQUOTE(@fieldName)
							) limit 1;
	
				SET @indxFL= @indxFL + 1;
				UNTIL @indxFL = JSON_LENGTH (@fieldLocations)
			END REPEAT;
	END IF;

        
        
        -- Read FundManager Details        
		SET @fundManagers	= 	JSON_EXTRACT(@schemeData, '$.value.fund_manager');
        SET @fmIndx	= 0;
        IF( JSON_LENGTH(@fundManagers)> 0)
        THEN	        
			REPEAT       
				SET @fundManagerData		=	JSON_EXTRACT(@fundManagers, CONCAT("$[", @fmIndx, "]"));
				SET @manager_name			=	trim(JSON_UNQUOTE(JSON_EXTRACT(@fundManagerData, '$.name')));
				SET @qualification			=	JSON_UNQUOTE(JSON_EXTRACT(@fundManagerData, '$.qualification'));
				SET @total_exp 				=	JSON_UNQUOTE(JSON_EXTRACT(@fundManagerData, '$.total_exp'));
				SET @managing_fund_since	=	JSON_UNQUOTE(JSON_EXTRACT(@fundManagerData, '$.managing_fund_since'));                
		
					IF EXISTS(SELECT document_detail_id FROM mf_json_fund_managers WHERE document_detail_id = @document_id 
			AND main_scheme_name = @main_scheme_name and is_migrated= false AND name = @manager_name ) THEN
BEGIN
	UPDATE mf_json_fund_managers SET name= @manager_name, managing_fund_since = IF( @managing_fund_since ='', null, @managing_fund_since), 
								qualification=@qualification, total_experience=@total_exp
  WHERE document_detail_id = @document_id 
			AND main_scheme_name = @main_scheme_name and is_migrated= false AND name = @manager_name ;
END;
ELSE
BEGIN
	  INSERT INTO `mf_json_fund_managers` (`document_detail_id`,`MainScheme_ID`,`main_scheme_name`,`name`,`managing_fund_since`,`qualification`,`total_experience`,`entered_user`,`is_migrated`)
					Values (@document_id, @MainScheme_ID, @main_scheme_name, @manager_name, IF( @managing_fund_since ='', null, @managing_fund_since), @qualification,@total_exp,@system_user_id ,false);
END;
END IF;
                            
				SET @fmIndx = @fmIndx + 1;
			UNTIL @fmIndx = JSON_LENGTH(@fundManagers)        
		END REPEAT;
        END IF;
        -- Read dividend details
        -- SET @dividends = JSON_EXTRACT(@schemeData, '$.value.dividend');
		-- SET @dIndx=0;        
        -- REPEAT       
		--  SET @dividendData =  JSON_EXTRACT(@dividends, CONCAT("$[", @dIndx, "]"));
		-- 	 SELECT	JSON_UNQUOTE(JSON_EXTRACT(@dividends, '$.type')),
		-- 			JSON_UNQUOTE(JSON_EXTRACT(@dividends, '$.record_date')),
		-- 			JSON_UNQUOTE(JSON_EXTRACT(@dividends, '$.declare_date')),
		-- 			JSON_UNQUOTE(JSON_EXTRACT(@dividends, '$.unit'));                
		-- 	 SET @dIndx = @dIndx + 1;
		-- 	 UNTIL @dIndx = JSON_LENGTH(@dividends)        
		--   END REPEAT;
         
           -- Read load details
		SET @loads = JSON_EXTRACT(@schemeData, '$.value.load');
		SET @loadindx=0;		
        IF (JSON_LENGTH(@loads)> 0)
        THEN        
			REPEAT			
				SET @loadData	=	JSON_EXTRACT(@loads, CONCAT("$[", @loadindx, "]"));
				SET @ltype 		=	JSON_UNQUOTE(JSON_EXTRACT(@loadData, '$.type'));		
                SET @ltype_Id	= 	(SELECT LoadType_ID FROM mf_master_loadtype where LoadType_Name = Cast(@ltype as CHAR)); 
				SET @lvalue 	=	JSON_UNQUOTE(JSON_EXTRACT(@loadData, '$.value'));
				SET @lcomment 	=	JSON_UNQUOTE(JSON_EXTRACT(@loadData, '$.comment'));
				
				IF EXISTS(SELECT document_detail_id FROM mf_json_loads WHERE document_detail_id = @document_id 
				and main_scheme_name = @main_scheme_name and is_migrated= false and type = @ltype and (value = @lvalue or value is null)) THEN
		BEGIN
			UPDATE mf_json_loads SET comment = @lcomment, load_type_id = @ltype_Id, type = @ltype, value = @lvalue
			WHERE document_detail_id = @document_id  and main_scheme_name = @main_scheme_name and is_migrated= false and type = @ltype and (value = @lvalue or value is null);
		END;
		ELSE
		BEGIN
			INSERT INTO   `mf_json_loads`	(`document_detail_id`,`MainScheme_ID`,`main_scheme_name`,`comment`,`load_type_id`,`type`,`value`,`entered_user`,`is_migrated`)
			Values ( @document_id, @MainScheme_ID,@main_scheme_name, @lcomment,@ltype_Id, @ltype, @lvalue, @system_user_id,false);
		END;
        END IF;
                            
                SET @loadindx = @loadindx + 1;
			UNTIL @loadindx = JSON_LENGTH(@loads)        
			END REPEAT;          
        END IF;
   /*     SET @matrics = JSON_EXTRACT(@schemeData, '$.value.matrics');
		SET @matindex=0;		
        REPEAT			
			SET @matricData = JSON_EXTRACT(@matrics, CONCAT("$[", @matindex, "]"));
			SELECT 	JSON_UNQUOTE(JSON_EXTRACT(@matricData, '$.name')),
					JSON_UNQUOTE(JSON_EXTRACT(@matricData, '$.value'));
			
            SET @matindex = @matindex + 1;
		UNTIL @matindex = JSON_LENGTH(@matrics)        
		END REPEAT;   */
        
        
        SET @indx = @indx + 1;
        UNTIL @indx = JSON_LENGTH(@records)        
END REPEAT;
END IF;

END