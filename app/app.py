from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
import datetime
import xml.etree.ElementTree as ET
from io import BytesIO
import json

app = Flask(__name__)

# URLs and Credentials (replace with your actual values)

#Please add URL here

def fetch_token():
    try:
        response = requests.post(AUTH_URL)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        print(f"Failed to fetch token: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error fetching token: {str(e)}")
    return None

def print_xml_structure(entry, namespaces):
    """Helper function to print detailed XML structure"""
    print("\n--- XML Entry Structure ---")
    
    # Try to find various potential order number locations
    potential_order_paths = [
        './/atom:content/m:properties/d:code',
        './/d:code',
        './/m:properties/d:code',
        './/atom:content/m:properties'
    ]
    
    for path in potential_order_paths:
        elements = entry.findall(path, namespaces)
        if elements:
            print(f"\nElements found for path {path}:")
            for elem in elements:
                print(f"Tag: {elem.tag}")
                print(f"Text: {elem.text}")
                print(f"Attributes: {elem.attrib}")
                print("---")

def fetch_orders(token, site_uid, start_date=None, end_date=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/xml"
    }
    
    # Set default date range if not provided
    if start_date is None or end_date is None:
        today = datetime.datetime.today()
        start_date = today.replace(year=today.year - 1, month=1, day=1).strftime('%Y-%m-%dT%H:%M:%S')
        end_date = today.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        end_date = (end_date + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
        start_date = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    
    url = GET_URL_TEMPLATE.format(site_uid=site_uid, start_date=start_date, end_date=end_date)
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            namespaces = {
                'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
                'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
                'atom': 'http://www.w3.org/2005/Atom'
            }
            orders = []
            
            for entry in root.findall('.//atom:entry', namespaces):
                print_xml_structure(entry, namespaces)
                
                # Extract date
                date_elem = entry.find('.//d:date', namespaces)
                date_value = 'N/A'
                if date_elem is not None and date_elem.text:
                    try:
                        if date_elem.text.startswith('/Date('):
                            timestamp = int(date_elem.text[6:-2]) / 1000
                            date_value = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                        elif 'T' in date_elem.text:
                            date_value = datetime.datetime.fromisoformat(date_elem.text.split('T')[0]).strftime('%Y-%m-%d')
                    except Exception as e:
                        print(f"Date parsing error: {e}")
                
                # Extract order number using code from HybrisCommerceOData.Order
                order_elem = entry.find('.//atom:content/m:properties/d:code', namespaces)
                order_no = 'N/A'
                if order_elem is not None and order_elem.text and order_elem.text.isdigit():
                    order_no = order_elem.text
                
                # Extract status
                status_elem = entry.find('.//atom:link[@title="status"]/m:inline/atom:entry/atom:content/m:properties/d:code', namespaces)
                order_status = 'N/A'
                if status_elem is not None and status_elem.text:
                    order_status = status_elem.text
                
                # Extract purchase order number
                po_elem = entry.find('.//d:purchaseOrderNumber', namespaces)
                purchase_order_no = 'N/A'
                if po_elem is not None and po_elem.text:
                    purchase_order_no = po_elem.text
                
                # Create order dictionary
                order = {
                    'date': date_value,
                    'order_status': order_status,
                    'order_no': order_no,
                    'purchaseOrderNumber': purchase_order_no
                }
                
                # Optional: Print parsed order for debugging
                print(f"Parsed Order: {order}")
                
                orders.append(order)
            
            # Remove duplicated rows with N/A values
            orders = [order for i, order in enumerate(orders) if i % 2 == 0 or (order['date'] != 'N/A' or order['order_status'] != 'N/A' or order['order_no'] != 'N/A' or order['purchaseOrderNumber'] != 'N/A')]
            
            return orders
        else:
            print(f"Error response for {site_uid}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception when fetching orders for {site_uid}: {str(e)}")
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_orders', methods=['POST'])
def fetch_orders_route():
    site_uid = request.form.get('site_uid')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    if start_date:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    token = fetch_token()
    if token:
        orders = fetch_orders(token, site_uid, start_date, end_date)
        if orders:
            return jsonify(orders)
    return jsonify([])

@app.route('/export_orders', methods=['POST'])
def export_orders():
    orders = request.json.get('orders')
    site_uid = request.json.get('site_uid')
    
    df = pd.DataFrame(orders)
    csv_data = df.to_csv(index=False)
    buffer = BytesIO()
    buffer.write(csv_data.encode('utf-8'))
    buffer.seek(0)
    
    # Format the file name based on the site_uid
    file_name = f"{site_uid}-orders.csv"
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=file_name
    )

@app.route('/fetch_order_counts', methods=['GET'])
def fetch_order_counts():
    site_uid = request.args.get('site')
    token = fetch_token()
    if token:
        today = datetime.datetime.today()
        yesterday = today - datetime.timedelta(days=1)
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        orders_today = fetch_orders(token, site_uid, today, today)
        orders_yesterday = fetch_orders(token, site_uid, yesterday, yesterday)
        orders_this_month = fetch_orders(token, site_uid, start_of_month, today)
        orders_this_year = fetch_orders(token, site_uid, start_of_year, today)
        return jsonify({
            'totalOrders': len(orders_today or []) + len(orders_yesterday or []) + len(orders_this_month or []) + len(orders_this_year or []),
            'todaysOrders': len(orders_today or []),
            'yesterdaysOrders': len(orders_yesterday or []),
            'thisMonthOrders': len(orders_this_month or []),
            'thisYearOrders': len(orders_this_year or [])
        })
    return jsonify({
        'totalOrders': 0,
        'todaysOrders': 0,
        'yesterdaysOrders': 0,
        'thisMonthOrders': 0,
        'thisYearOrders': 0
    })

if __name__ == '__main__':
    app.run(debug=True)