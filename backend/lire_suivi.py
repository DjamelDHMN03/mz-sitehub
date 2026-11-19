from openpyxl import load_workbook

path = r'C:\Users\WINDOWS 11\OneDrive\Desktop\MZ-SITEHUB-COMPLET\MZ-SITEHUB\backend\SUIVI_NETTOYE.xlsx'
wb = load_workbook(path, data_only=True, read_only=True)
for ws in wb.worksheets:
    print("=" * 60)
    print("FEUILLE :", ws.title, "| lignes:", ws.max_row, "| colonnes:", ws.max_column)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        print(i + 1, row)
        if i >= 7:
            break
