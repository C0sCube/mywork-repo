import re, os, sys
from collections import defaultdict

class dict_crud():
    
    def __init__(self, name, age):
      self.name = name
      self.age = age
      
    #NESTED DICT CRUD OPS
    # @staticmethod
    # def merge_nested_dicts(*dicts):
    #     return {key: reduce(lambda acc, d: {**acc, **d.get(key, {})}, dicts, {}) for key in dicts[0].keys()}

    @staticmethod
    def drop_empty_dict_values(final_dict:dict):
        finally_dict = {}
        for fund, content in final_dict.items():
            non_empty_dict = {}
            for key, value in content.items():
                if len(value)>=1:
                    non_empty_dict[key] = value
            finally_dict[fund] = non_empty_dict
        return finally_dict
    
    @staticmethod
    def drop_selected_dict_values(final_dict:dict, patterns:list):
        finally_dict = {}
        for fund, content in final_dict.items():
            clean_dict = {}
            for k, v in content.items():
                if not any(re.search(pattern, k) for pattern in patterns):
                    clean_dict[k] = v
            finally_dict[fund] = clean_dict
        return finally_dict
    
    @staticmethod
    def select_dict_with_keys(final_dict: dict, patterns: list):
        selected_dict = {}
        for fund, content in final_dict.items():
            filtered_dict = {k: v for k, v in content.items() if any(re.search(pattern, k) for pattern in patterns)}
            selected_dict[fund] = filtered_dict

        return selected_dict
    
    @staticmethod
    def drop_keys_by_regex(data, patterns):
        if not isinstance(data, dict):
            return data
        
        regex_list = [re.compile(pattern) for pattern in patterns]
        final_dict = {}
        for key, value in data.items():
            if any(regex.match(key) for regex in regex_list):
                continue
            
            if isinstance(value, dict): #dict
                final_dict[key] = dict_crud.drop_keys_by_regex(value, patterns)
            elif isinstance(value, list): #list
                final_dict[key] = [dict_crud.drop_keys_by_regex(item, patterns) if isinstance(item, dict) else item for item in value]
            else:
                final_dict[key] = value
        
        return final_dict
    
    @staticmethod
    def merge_key_values(data, key1, key2):
        if isinstance(data, dict):
            if key1 in data and key2 in data:
                val1, val2 = data[key1], data[key2]

                if isinstance(val1, list) and isinstance(val2, list):
                    data[key1] = val1 + val2  # Merge lists
                elif isinstance(val1, dict) and isinstance(val2, dict):
                    merged_dict = defaultdict(dict, val1)
                    for k, v in val2.items():
                        if k in merged_dict and isinstance(merged_dict[k], dict) and isinstance(v, dict):
                            merged_dict[k].update(v)  # Merge nested dicts
                        else:
                            merged_dict[k] = v
                    data[key1] = dict(merged_dict)
                elif isinstance(val1, str) and isinstance(val2, str):
                    data[key1] = val1 + " " + val2  # Concatenate strings
                else:
                    data[key1] = [val1, val2]  # Handle mixed types as a list

                del data[key2]  # Remove key2 after merging

            for k, v in data.items():  # Recursively merge nested dictionaries
                dict_crud.merge_key_values(v, key1, key2)

        elif isinstance(data, list):  # Handle lists of dictionaries
            for item in data:
                dict_crud.merge_key_values(item, key1, key2)

        return data