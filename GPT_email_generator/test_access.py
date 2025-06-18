from sheet_subscriber import connect_sheet

sheet = connect_sheet()
print("✅ Connected!")
print("🔽 First row of your sheet:", sheet.row_values(1))
