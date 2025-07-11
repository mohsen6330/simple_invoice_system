import sqlite3

DATABASE_NAME = "invoicing_system.db"

def get_db_connection():
    """
    ينشئ اتصالاً بقاعدة البيانات.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        if conn:
            conn.close()
        return None

def create_tables():
    """
    يقوم بإنشاء جميع الجداول اللازمة إذا لم تكن موجودة.
    """
    conn = get_db_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()

        # جدول الفواتير (للمعلومات الأساسية)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                client_name TEXT NOT NULL,
                client_tax_id TEXT,
                client_address TEXT,
                merchant_name TEXT,
                merchant_tax_id TEXT,
                merchant_address TEXT,
                invoice_date TEXT NOT NULL,
                total_before_tax REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                total_with_tax REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'Draft'
            );
        """)

        # جدول بنود الفواتير (لتفاصيل المنتجات)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                item_total REAL NOT NULL,
                item_total_with_tax REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            );
        """)
        
        conn.commit()
        print("Database tables created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")
    finally:
        if conn:
            conn.close()

def save_invoice_data(invoice_data, items_data):
    """
    يحفظ بيانات الفاتورة وبنودها في قاعدة البيانات.
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        
        # حفظ بيانات الفاتورة الرئيسية
        cursor.execute("""
            INSERT INTO invoices (
                invoice_number, client_name, client_tax_id, client_address,
                merchant_name, merchant_tax_id, merchant_address, invoice_date,
                total_before_tax, tax_amount, total_with_tax
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_data['invoice_number'],
            invoice_data['client_name'],
            invoice_data['client_tax_id'],
            invoice_data['client_address'],
            invoice_data['merchant_name'],
            invoice_data['merchant_tax_id'],
            invoice_data['merchant_address'],
            invoice_data['invoice_date'],
            invoice_data['total_before_tax'],
            invoice_data['tax_amount'],
            invoice_data['total_with_tax']
        ))
        
        invoice_id = cursor.lastrowid
        
        # حفظ بنود الفاتورة
        for item in items_data:
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id, product_name, quantity, unit_price,
                    item_total, item_total_with_tax
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item['product_name'],
                item['quantity'],
                item['unit_price'],
                item['item_total'],
                item['item_total_with_tax']
            ))

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving invoice data: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_invoice_by_id(invoice_id):
    """
    يجلب فاتورة واحدة من قاعدة البيانات بواسطة ID.
    """
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        invoice = cursor.fetchone()
        return invoice
    except sqlite3.Error as e:
        print(f"Error fetching invoice: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_invoice_items(invoice_id):
    """
    يجلب بنود فاتورة معينة من قاعدة البيانات.
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        items = cursor.fetchall()
        return items
    except sqlite3.Error as e:
        print(f"Error fetching invoice items: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_invoices():
    """
    يجلب جميع الفواتير من قاعدة البيانات.
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices ORDER BY invoice_date DESC")
        invoices = cursor.fetchall()
        return invoices
    except sqlite3.Error as e:
        print(f"Error fetching all invoices: {e}")
        return []
    finally:
        if conn:
            conn.close()

def initialize_db():
    """
    تهيئة قاعدة البيانات وإنشاء الجداول.
    """
    create_tables()