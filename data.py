"""
Data access layer target module.

Move Supabase + CSV functions from legacy/runtime.py here:
- get_supabase_client
- sb_select / sb_insert / sb_delete_matching
- df_from_supabase
- load_log / save_set_auto
- load_custom_plan / save_custom_plan
"""

import pandas as pd

def empty_df() -> pd.DataFrame:
    return pd.DataFrame()
