import re
import unicodedata
import pandas as pd
from pathlib import Path

BRONZE_DIR = Path(__file__).resolve().parents[4] / "data" / "bronze"
SILVER_DIR = Path(__file__).resolve().parents[4] / "data" / "silver"
SILVER_DIR.mkdir(parents=True, exist_ok=True)

def _normalize_text(s: str) -> str:
    if pd.isna(s):
        return ""
    
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9 _-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s

def _coerce_price(x):
    if pd.isna(x):
        return None
    
    s = str(x)
    s = re.sub(r"[^0-9,.\-]", "", s)

    if "," in s and "." not in s:
        s = s.replace(",", ".")

    if "." in s and "," in s:
        s = s.replace(",", "")

    try:
        return float(s)
    
    except Exception:
        return None

def _pick_bronze_csv() -> Path:
    cands = list(BRONZE_DIR.glob("books*.csv"))

    if not cands:
        raise SystemExit(f"[ERRO] Nenhum CSV encontrado em {BRONZE_DIR} (esperado books*.csv).")
    
    cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return cands[0]

INPUT_CSV = _pick_bronze_csv()
print(f"[INFO] Lendo bronze: {INPUT_CSV}")

df = pd.read_csv(INPUT_CSV)
orig_rows = len(df)

if "link" in df.columns and "product_url" not in df.columns:
    df = df.rename(columns={"link": "product_url"})

if "book_title" in df.columns:
    df["book_title"] = df["book_title"].astype(str).map(_normalize_text)
    df["title"] = df["book_title"]
elif "title" in df.columns:
    df["title"] = df["title"].astype(str).map(_normalize_text)

if "category" in df.columns:
    df["category"] = df["category"].astype(str).map(_normalize_text)

if "raw_price" in df.columns:
    df["raw_price"] = df["raw_price"].map(_coerce_price)

if "rating" in df.columns:
    df["rating"] = (
        pd.to_numeric(df["rating"], errors="coerce")
        .fillna(0)
        .astype(int)
        .clip(0, 5)
    )

if "product_url" in df.columns:
    df["product_url"] = df["product_url"].astype(str).str.strip()

prior = [c for c in ["title", "book_title", "category", "raw_price", "rating", "product_url"] if c in df.columns]
cols  = prior + [c for c in df.columns if c not in prior]
df = df[cols]

out_parquet = SILVER_DIR / "books.parquet"
out_csv     = SILVER_DIR / "books.csv"

df.to_csv(out_csv, index=False, encoding="utf-8-sig")

parquet_ok, parquet_err = True, None

try:
    df.to_parquet(out_parquet, index=False)

except Exception as e:
    parquet_ok, parquet_err = False, e

print(f"[INFO] Linhas de entrada: {orig_rows} | Linhas de saída: {len(df)}")
print(f"[OK] CSV: {out_csv}")

if parquet_ok:
    print(f"[OK] Parquet: {out_parquet}")
else:
    print(f"[WARN] Parquet falhou ({parquet_err})")
