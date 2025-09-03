def parse_processes(df_raw: pd.DataFrame) -> dict:
    """
    Parse a 'Processes' table from Excel in a tolerant way.
    Expected fields (many aliases accepted):
      - name:  process | step | operation | name | process name
      - co2e:  co2e | co2e (kg) | co2 | emission | factor | kg per unit
      - unit:  unit | units | uom
    If no obvious columns are found, we fall back to heuristics:
      * first text-like column becomes the name
      * first numeric column becomes the emission factor
      * unit is optional (first short text-like column with few uniques)
    """
    if df_raw is None or df_raw.empty:
        return {}

    df = _normalize_cols(df_raw)

    def pick(aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    # 1) try aliases
    col_proc = pick(["process", "step", "operation", "name", "process name"])
    col_co2  = pick(["co2e", "co2e (kg)", "co2", "emission", "factor", "kg per unit", "kg/unit"])
    col_unit = pick(["unit", "units", "uom"])

    # 2) heuristics if missing
    if not col_proc:
        # pick first object/string-like column with many unique non-empty values
        obj_cols = [c for c in df.columns if df[c].dtype == object]
        cand = None
        for c in obj_cols:
            vals = df[c].dropna().astype(str).str.strip()
            if vals.nunique() >= max(5, int(len(vals) * 0.5)):
                cand = c
                break
        col_proc = cand or (obj_cols[0] if obj_cols else None)

    if not col_co2:
        # pick first numeric-like column
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            # try to coerce
            for c in df.columns:
                try:
                    pd.to_numeric(df[c])
                    num_cols.append(c)
                except Exception:
                    pass
        col_co2 = num_cols[0] if num_cols else None

    # unit is optional; try to guess short-text column
    if not col_unit:
        txt_cols = [c for c in df.columns if df[c].dtype == object]
        cand = None
        for c in txt_cols:
            vals = df[c].dropna().astype(str).str.strip()
            # short tokens and small cardinality look like units
            if vals.map(len).mean() <= 6 and vals.nunique() <= 10:
                cand = c
                break
        col_unit = cand

    # If we still don't have the two essentials, return {}
    if not col_proc or not col_co2:
        return {}

    out = {}
    for _, r in df.iterrows():
        name = str(r[col_proc]).strip() if pd.notna(r[col_proc]) else ""
        if not name:
            continue
        try:
            co2e = extract_number(r[col_co2]) if pd.notna(r[col_co2]) else 0.0
        except Exception:
            co2e = 0.0
        unit = str(r[col_unit]).strip() if col_unit and pd.notna(r.get(col_unit, None)) else ""
        out[name] = {"CO₂e": co2e, "Unit": unit}
    return out
