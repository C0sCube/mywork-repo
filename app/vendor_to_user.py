import datetime, os, json

class VendorMapper:
    
    @staticmethod
    def _generate_map_value(scheme_count:int,data:dict):
        record_value = {}
        
        #singular
        record_value["min_addl_amt"] = data.get("min_addl_amt", "")
        record_value["min_addl_amt_multiple"] = data.get("min_addl_amt_multiple", "")
        record_value["min_amt"] = data.get("min_amt", "")
        record_value["min_amt_multiple"] = data.get("min_amt_multiple", "")
        record_value["monthly_aaum_date"] = data.get("monthly_aaum_date", "")
        record_value["monthly_aaum_value"] = data.get("monthly_aaum_value", "")
        record_value["mutual_fund_name"] = data.get("mutual_fund_name", "")
        record_value["scheme_launch_date"] = data.get("scheme_launch_date", "")
        record_value["main_scheme_name"] = data.get("main_scheme_name", "")
        record_value["amc_name"] = data.get("amc_name", "")
        record_value["benchmark_index"] = [data.get("benchmark_index","")]
        
        #metrics
        metrics = []
        for key,value in data['metrics'].items():
            if value:
                metrics.append({"name":key,"value":str(value)})
        record_value["metrics"] = metrics
        
        #load
        load = []
        for key,value in data['load'].items():
            load.append({"type":key,"comment":str(value)})
        record_value["load"] = load
        
        #fund manager
        record_value["fund_manager"] = data.get("fund_manager",[])
    
        #field_location
        page_number = str(data["page_number"][0]+1)
        field_location = {
            "amc_name": page_number,
            "benchmark_index": page_number,
            "count": scheme_count, 
            # "fund_manager_managing_fund_since": page_number,
            # "fund_manager_name": page_number,
            # "fund_manager_qualification":page_number,
            # "fund_manager_total_exp": page_number,
            "main_scheme_name": page_number,
            "min_addl_amt": page_number,
            "min_addl_amt_multiple": page_number,
            "min_amt": page_number,
            "min_amt_multiple": page_number,
            "monthly_aaum_date": page_number,
            "monthly_aaum_value": page_number,
            "mutual_fund_name": page_number,
            "scheme_launch_date": page_number
        }
        
        for content in record_value["metrics"]:
            metric_name = content["name"]
            metric = f"metrics_{metric_name}"
            field_location[metric] = page_number
        
        for content in record_value["load"]:
            type_ = content['type'].replace("_load", "")
            key = f"load_{type_}"
            if content['comment']:
                field_location[key] = page_number
                
        if record_value["fund_manager"]:
            inst = record_value['fund_manager'][0]
            for key,value in inst.items():
                if value:
                    add_key = f"fund_manager_{key}"
                    field_location[add_key] = page_number
        
        record_value["field_location"] = [dict(sorted(field_location.items()))]

        return dict(sorted(record_value.items()))
    
    
    def map_to_fink(self,data,filename):
        scheme_count = len(data)
        final_container = {
            "metadata":{
                "document_name":filename,
                "file_type":"",
                "process_date": f"{datetime.datetime.now().strftime('%Y%m%d_%H:%M')}"
            },
            "records":[]
        }
        for key,content in data.items():
            final_container["records"].append({"value":VendorMapper._generate_map_value(scheme_count,content)})
        
        return final_container
    
    
if __name__ == "__main__":
    map_vendor = VendorMapper()
    
    input_folder = os.path.join(os.getcwd(), "sql_learn", "json", "feb25latest")
    output_folder = os.path.join(os.getcwd(),"data","feb25_map")
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        print(f"Doing For: {filename}")
        if filename.endswith(".json"):
            file_path = os.path.join(input_folder, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            mapped_data = map_vendor.map_to_fink(json_data,filename)

            output_path = os.path.join(output_folder, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(mapped_data, f, indent=2, ensure_ascii=False)

    print(f"Mapping complete. Output saved in: {output_folder}")
    
    