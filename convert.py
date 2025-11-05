import jpype
import tabula
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

# ✅ 1. Specify the full JVM path manually
JVM_PATH = r"C:\Program Files\Java\jdk-21\bin\server\jvm.dll"

# ✅ 2. Start JVM if not started
if not jpype.isJVMStarted():
    try:
        jpype.startJVM(JVM_PATH)
        print("✅ JVM started successfully.")
    except Exception as e:
        print("⚠️ JVM start failed:", e)
        print("Falling back to Tabula subprocess mode.")

# ✅ 3. Read tables from the PDF
pdf_path = "cutoff.pdf"
print("📄 Extracting tables from:", pdf_path)

try:
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
    if not tables:
        raise ValueError("No tables detected. Check PDF quality or try lattice mode.")
except Exception as e:
    print("⚠️ Tabula failed with error:", e)
    print("Trying lattice mode (better for bordered tables)...")
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, lattice=True)

# ✅ 4. Combine and save as CSV
df = pd.concat(tables, ignore_index=True)
df.to_csv("du_cutoff.csv", index=False, encoding="utf-8-sig")

print("✅ Successfully extracted", len(tables), "tables and saved as du_cutoff.csv")
