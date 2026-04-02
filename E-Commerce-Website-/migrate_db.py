import sqlite3

def migrate():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(products)")
    columns = [info[1] for info in cursor.fetchall()]
    
    fields_to_add = [
        "benefits",
        "how_to_use",
        "ayurvedic_properties",
        "precautions"
    ]
    
    for field in fields_to_add:
        if field not in columns:
            print(f"Adding column {field} to products table...")
            cursor.execute(f"ALTER TABLE products ADD COLUMN {field} TEXT")
        else:
            print(f"Column {field} already exists.")
            
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
