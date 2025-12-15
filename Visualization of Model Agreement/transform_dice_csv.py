import pandas as pd
import re
import sys


def clean_method_name(method):
    method = method.decode() if isinstance(method, bytes) else str(method)

    if re.search(r"TotalSegmentator_\d+\.\d+", method):
        return method

    return re.sub(r"\.\d+$", "", method)

def transform_csv(input_path, output_path):
    df = pd.read_csv(input_path, header=None)

    case_ids = df.iloc[0, 1:].fillna("Unknown_Case").astype(str).tolist()

    methods = [clean_method_name(m) for m in df.iloc[1, 1:].tolist()]

    df = df.iloc[3:].reset_index(drop=True)  
    df.columns = ["segment"] + methods  
    df = df.reset_index(drop=True) 

    df.loc[-1] = ["caseID"] + case_ids 
    df = df.sort_index().reset_index(drop=True) 

    df_melted = df.melt(id_vars=["segment"], var_name="method", value_name="dsc")

    df_melted["dsc"] = df_melted["dsc"].astype(str).replace("nan", "")

    df_melted["caseID"] = df_melted[df_melted["segment"] == "caseID"]["dsc"]
    df_melted["caseID"] = df_melted["caseID"].ffill() 
    df_melted = df_melted[df_melted["segment"] != "caseID"] 

    df_melted = df_melted[["segment", "method", "dsc", "caseID"]]

    df_melted.to_csv(output_path, index=False, na_rep="")  
    print(f"Saved transformed CSV to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python transform_csv.py <input_pivot_csv> <output_long_csv>")
        sys.exit(1)

    transform_csv(sys.argv[1], sys.argv[2])
