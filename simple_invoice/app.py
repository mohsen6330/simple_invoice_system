import os
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from xhtml2pdf import pisa
from io import BytesIO

# Configuration
DATABASE_NAME = 'invoicing_system.db'

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database initialization
def init_db():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME, timeout=10)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_number TEXT PRIMARY KEY,
                client_name TEXT,
                client_tax_id TEXT,
                client_address TEXT,
                merchant_name TEXT,
                merchant_tax_id TEXT,
                merchant_address TEXT,
                invoice_date TEXT,
                total_before_tax REAL,
                tax_amount REAL,
                total_with_tax REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT,
                product_name TEXT,
                quantity REAL,
                unit_price REAL,
                item_total REAL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_number)
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

# HTML to PDF converter
def html_to_pdf(html_content):
    result_file = BytesIO()
    
    font_folder = os.path.join(app.root_path, 'fonts')

    def link_callback(uri, rel):
        # A custom callback to help xhtml2pdf find local files
        if uri.lower().startswith('tajawal-regular.ttf'):
            path = os.path.join(font_folder, 'Tajawal-Regular.ttf')
            if os.path.exists(path):
                return path
            else:
                print(f"Error: Font file not found at: {path}")
                return None
        elif uri.lower().startswith('tajawal-bold.ttf'):
            path = os.path.join(font_folder, 'Tajawal-Bold.ttf')
            if os.path.exists(path):
                return path
            else:
                print(f"Error: Font file not found at: {path}")
                return None
        return uri

    pisa_status = pisa.CreatePDF(
        BytesIO(html_content.encode('utf-8')),
        dest=result_file,
        encoding='utf-8',
        link_callback=link_callback
    )
    if not pisa_status.err:
        result_file.seek(0)
        return result_file
    
    print(f"Pisa Error: {pisa_status.err}")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_invoice')
def create_invoice():
    today = datetime.now().strftime('%Y-%m-%d')
    default_data = {
        'merchant_name': 'شركة النسور الذهبية',
        'merchant_tax_id': '0000000000000000',
        'merchant_address': 'القصيم بريدة',
        'client_name': 'بنشر آفاق الناضصرية',
        'client_tax_id': '111111111111111',
        'client_address': 'القصيم بريدة',
    }
    return render_template('create_invoice.html', today=today, default_data=default_data)

@app.route('/invoices')
def invoices():
    all_invoices = []
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM invoices')
        all_invoices = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
    return render_template('invoices.html', invoices=all_invoices)

@app.route('/save_invoice', methods=['POST'])
def save_invoice():
    conn = None
    try:
        data = request.json
        
        invoice_data = {
            'invoice_number': str(uuid.uuid4()),
            'client_name': data.get('client_name'),
            'client_tax_id': data.get('client_tax_id'),
            'client_address': data.get('client_address'),
            'merchant_name': data.get('merchant_name'),
            'merchant_tax_id': data.get('merchant_tax_id'),
            'merchant_address': data.get('merchant_address'),
            'invoice_date': data.get('invoice_date'),
            'total_before_tax': data.get('grand_total'),
            'tax_amount': data.get('tax_amount'),
            'total_with_tax': data.get('grand_total_with_tax')
        }
        
        items_data = data.get('items', [])
        
        conn = sqlite3.connect(DATABASE_NAME, timeout=10)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO invoices (
                invoice_number, client_name, client_tax_id, client_address,
                merchant_name, merchant_tax_id, merchant_address,
                invoice_date, total_before_tax, tax_amount, total_with_tax
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_data['invoice_number'], invoice_data['client_name'], invoice_data['client_tax_id'], invoice_data['client_address'],
            invoice_data['merchant_name'], invoice_data['merchant_tax_id'], invoice_data['merchant_address'],
            invoice_data['invoice_date'], invoice_data['total_before_tax'], invoice_data['tax_amount'], invoice_data['total_with_tax']
        ))
        
        for item in items_data:
            cursor.execute('''
                INSERT INTO invoice_items (
                    invoice_id, product_name, quantity, unit_price, item_total
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                invoice_data['invoice_number'], item['product_name'], item['quantity'], item['price'], item['total']
            ))

        conn.commit()
        
        return jsonify({'success': True, 'message': 'Invoice saved successfully.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/generate_pdf/<invoice_id>')
def generate_pdf(invoice_id):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE invoice_number = ?', (invoice_id,))
        invoice = cursor.fetchone()
        
        if not invoice:
            return "Invoice not found.", 404
        
        cursor.execute('SELECT * FROM invoice_items WHERE invoice_id = ?', (invoice_id,))
        items = cursor.fetchall()
        
        html = render_template('invoice_template.html', invoice=invoice, items=items)
        pdf = html_to_pdf(html)
        
        if pdf:
            return send_file(
                pdf,
                as_attachment=True,
                download_name=f'فاتورة_{invoice["invoice_number"]}.pdf',
                mimetype='application/pdf'
            )
        
        return 'Failed to generate PDF.', 500
    except Exception as e:
        print(f"PDF generation error: {e}")
        return 'Failed to generate PDF.', 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    if not os.path.exists(DATABASE_NAME):
        init_db()
    
    app.run(debug=False, use_reloader=False)