# Realize the pos system
# Author: Renjie Zhou
# StudentId: W20110010

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class Product:
    id: int
    name: str
    price: float
    category: str = "General"
    barcode: str = ""
    stock: int = 0
    min_stock: int = 5
    active: bool = True

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__dataclass_fields__.values()}


@dataclass
class OrderItem:
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    discount: float = 0.0

    @property
    def subtotal(self):
        return (self.unit_price * self.quantity) - self.discount


@dataclass
class Order:
    order_id: str
    items: List[OrderItem] = field(default_factory=list)
    member_id: Optional[str] = None
    payment_method: str = "Cash"
    payment_status: str = "Pending"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items)

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)

    def add_item(self, product_id: int, product_name: str, unit_price: float, quantity: int = 1):
        for item in self.items:
            if item.product_id == product_id:
                item.quantity += quantity
                return

        self.items.append(OrderItem(product_id, product_name, unit_price, quantity))

    def remove_item(self, product_id: int):
        self.items = [item for item in self.items if item.product_id != product_id]

class Database:
    def __init__(self, db_path="pos.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            barcode TEXT,
            stock INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 5,
            active BOOLEAN DEFAULT 1
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            member_id TEXT,
            payment_method TEXT,
            payment_status TEXT,
            total_amount REAL,
            created_at TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            product_id INTEGER,
            product_name TEXT,
            unit_price REAL,
            quantity INTEGER,
            discount REAL DEFAULT 0,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            member_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0
        )
        ''')

        conn.commit()
        conn.close()
        self.init_sample_data()

    def init_sample_data(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            sample_products = [
                ('Coca Cola 330ml', 3.00, 'Drinks', '6901234567890', 100, 10),
                ('Noodles Beef Flavor', 4.50, 'Food', '6923456789012', 50, 20),
                ('Tissue Paper 120pcs', 12.80, 'Daily', '6934567890123', 30, 5),
                ('Shampoo 400ml', 45.90, 'Care', '6945678901234', 20, 5),
                ('Oreo Cookies', 8.50, 'Snack', '6956789012345', 40, 10),
            ]

            cursor.executemany('''
            INSERT INTO products (name, price, category, barcode, stock, min_stock)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', sample_products)

            sample_members = [
                ('M001', 'John Doe', '13800138000', 500, 8500.00),
                ('M002', 'Jane Smith', '13900139000', 200, 1800.00),
            ]

            cursor.executemany('''
            INSERT INTO members (member_id, name, phone, points, total_spent)
            VALUES (?, ?, ?, ?, ?)
            ''', sample_members)

            conn.commit()
        conn.close()

    def get_product(self, product_id: int) -> Optional[Product]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ? AND active = 1", (product_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Product(
                id=row['id'],
                name=row['name'],
                price=row['price'],
                category=row['category'],
                barcode=row['barcode'],
                stock=row['stock'],
                min_stock=row['min_stock'],
                active=bool(row['active'])
            )
        return None

    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE barcode = ? AND active = 1", (barcode,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Product(
                id=row['id'],
                name=row['name'],
                price=row['price'],
                category=row['category'],
                barcode=row['barcode'],
                stock=row['stock'],
                min_stock=row['min_stock'],
                active=bool(row['active'])
            )
        return None

    def search_products(self, keyword: str = "") -> List[Product]:
        conn = self.get_connection()
        cursor = conn.cursor()

        if keyword:
            cursor.execute('''
            SELECT * FROM products 
            WHERE (name LIKE ? OR barcode LIKE ?) AND active = 1
            ''', (f'%{keyword}%', f'%{keyword}%'))
        else:
            cursor.execute("SELECT * FROM products WHERE active = 1")

        rows = cursor.fetchall()
        conn.close()

        return [
            Product(
                id=row['id'],
                name=row['name'],
                price=row['price'],
                category=row['category'],
                barcode=row['barcode'],
                stock=row['stock'],
                min_stock=row['min_stock'],
                active=bool(row['active'])
            ) for row in rows
        ]

    def update_stock(self, product_id: int, quantity: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE products 
            SET stock = stock - ?
            WHERE id = ? AND stock >= ?
            ''', (quantity, product_id, quantity))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except:
            return False

    def save_order(self, order: Order) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO orders (order_id, member_id, payment_method, payment_status, total_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (order.order_id, order.member_id, order.payment_method,
                  order.payment_status, order.total, order.created_at))

            for item in order.items:
                cursor.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, discount)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (order.order_id, item.product_id, item.product_name,
                      item.unit_price, item.quantity, item.discount))

                self.update_stock(item.product_id, item.quantity)

            if order.member_id:
                cursor.execute('''
                UPDATE members 
                SET total_spent = total_spent + ?, 
                    points = points + CAST(? * 10 AS INTEGER)
                WHERE member_id = ?
                ''', (order.total, order.total, order.member_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving order: {e}")
            return False

    def get_daily_sales(self, date: str = None) -> List[Dict]:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT 
            COUNT(*) as order_count,
            SUM(total_amount) as total_sales,
            AVG(total_amount) as avg_order
        FROM orders 
        WHERE DATE(created_at) = ?
        ''', (date,))

        result = cursor.fetchone()
        conn.close()

        if result and result['order_count']:
            return dict(result)
        return {'order_count': 0, 'total_sales': 0, 'avg_order': 0}

    def get_member(self, member_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

class POSSystem:
    def __init__(self):
        self.db = Database()
        self.current_order: Optional[Order] = None

    def start_order(self, member_id: str = None) -> Order:
        self.current_order = Order("", member_id=member_id)
        return self.current_order

    def scan_product(self, product_id: int, quantity: int = 1) -> Tuple[bool, str]:
        if not self.current_order:
            return False, "No active order"

        product = self.db.get_product(product_id)
        if not product:
            return False, f"Product {product_id} not found"

        if product.stock < quantity:
            return False, f"Insufficient stock. Only {product.stock} available"

        self.current_order.add_item(product.id, product.name, product.price, quantity)
        return True, f"Added {product.name} x {quantity}"

    def scan_barcode(self, barcode: str, quantity: int = 1) -> Tuple[bool, str]:
        product = self.db.get_product_by_barcode(barcode)
        if product:
            return self.scan_product(product.id, quantity)
        return False, f"Barcode {barcode} not found"

    def process_payment(self, payment_method: str, amount: float) -> Tuple[bool, str, float]:
        if not self.current_order:
            return False, "No order to process", 0.0

        if amount < self.current_order.total:
            return False, f"Insufficient amount. Need {self.current_order.total - amount:.2f} more", 0.0

        self.current_order.payment_method = payment_method
        self.current_order.payment_status = "Paid"

        success = self.db.save_order(self.current_order)
        if not success:
            return False, "Failed to save order", 0.0

        change = amount - self.current_order.total
        receipt = self.generate_receipt()

        completed_order = self.current_order
        self.current_order = None

        return True, receipt, change

    def generate_receipt(self) -> str:
        if not self.current_order:
            return ""

        receipt = [
            "=" * 50,
            "RECEIPT",
            "=" * 50,
            f"Order ID: {self.current_order.order_id}",
            f"Time: {self.current_order.created_at}",
            "-" * 50
        ]

        for item in self.current_order.items:
            receipt.append(
                f"{item.product_name[:20]:20} {item.quantity:3d} x ${item.unit_price:6.2f} = ${item.subtotal:7.2f}")

        receipt.extend([
            "-" * 50,
            f"Total: ${self.current_order.total:9.2f}",
            f"Payment: {self.current_order.payment_method}",
            "=" * 50,
            "Thank you for your purchase!",
            "=" * 50
        ])

        return "\n".join(receipt)

    def cancel_order(self) -> bool:
        if self.current_order:
            self.current_order = None
            return True
        return False

class POSApplication:
    def __init__(self):
        self.system = POSSystem()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_header(self):
        print("=" * 50)
        print("POS SYSTEM v2.0")
        print("=" * 50)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)

    def main_menu(self):
        while True:
            self.clear_screen()
            self.show_header()

            print("1. Start New Order")
            print("2. Scan Product")
            print("3. View Current Order")
            print("4. Process Payment")
            print("5. Search Products")
            print("6. View Sales Report")
            print("7. Exit")
            print("-" * 50)

            choice = input("Select option (1-7): ")

            if choice == '1':
                self.new_order()
            elif choice == '2':
                self.scan_product()
            elif choice == '3':
                self.view_order()
            elif choice == '4':
                self.process_payment()
            elif choice == '5':
                self.search_products()
            elif choice == '6':
                self.sales_report()
            elif choice == '7':
                print("Goodbye!")
                break
            else:
                print("Invalid option")

            input("\nPress Enter to continue...")

    def new_order(self):
        print("\n--- New Order ---")
        member_id = input("Member ID (press Enter for none): ").strip() or None
        self.system.start_order(member_id)
        print(f"Order started: {self.system.current_order.order_id}")

    def scan_product(self):
        print("\n--- Scan Product ---")

        if not self.system.current_order:
            print("Start a new order first")
            return

        print("1. Enter Product ID")
        print("2. Scan Barcode")
        choice = input("Select method: ")

        if choice == '1':
            try:
                product_id = int(input("Product ID: "))
                quantity = int(input("Quantity (default 1): ") or "1")
                success, msg = self.system.scan_product(product_id, quantity)
                print(msg)
            except ValueError:
                print("Invalid input")

        elif choice == '2':
            barcode = input("Barcode: ")
            quantity = int(input("Quantity (default 1): ") or "1")
            success, msg = self.system.scan_barcode(barcode, quantity)
            print(msg)

    def view_order(self):
        if not self.system.current_order:
            print("No active order")
            return

        print("\n--- Current Order ---")
        print(f"Order ID: {self.system.current_order.order_id}")
        print("-" * 50)

        if not self.system.current_order.items:
            print("Empty order")
        else:
            for item in self.system.current_order.items:
                print(f"{item.product_name:20} {item.quantity:3d} x ${item.unit_price:6.2f}")

        print("-" * 50)
        print(f"Total: ${self.system.current_order.total:.2f}")

    def process_payment(self):
        if not self.system.current_order:
            print("No order to pay")
            return

        print("\n--- Process Payment ---")
        print(f"Total Amount: ${self.system.current_order.total:.2f}")

        print("\nPayment Methods:")
        print("1. Cash")
        print("2. Card")
        print("3. Mobile")

        method = input("Select method: ")
        methods = {'1': 'Cash', '2': 'Card', '3': 'Mobile'}

        try:
            amount = float(input(f"Amount paid: $"))
            success, receipt, change = self.system.process_payment(
                methods.get(method, 'Cash'),
                amount
            )

            if success:
                print("\nPayment successful!")
                print(receipt)
                if change > 0:
                    print(f"Change: ${change:.2f}")
            else:
                print(f"Payment failed: {receipt}")
        except ValueError:
            print("Invalid amount")

    def search_products(self):
        print("\n--- Search Products ---")
        keyword = input("Search keyword: ")
        products = self.system.db.search_products(keyword)

        if products:
            print(f"\nFound {len(products)} products:")
            for product in products:
                stock_status = "LOW" if product.stock <= product.min_stock else "OK"
                print(
                    f"{product.id:3d}. {product.name:25} ${product.price:6.2f} Stock: {product.stock:3d} [{stock_status}]")
        else:
            print("No products found")

    def sales_report(self):
        print("\n--- Sales Report ---")
        date = input("Date (YYYY-MM-DD) or Enter for today: ")
        report = self.system.db.get_daily_sales(date)

        print(f"\nSales Summary:")
        print(f"Orders: {report['order_count']}")
        print(f"Total Sales: ${report['total_sales']:.2f}")
        print(f"Average Order: ${report['avg_order']:.2f}")

    def run(self):
        print("POS System Starting...")
        self.main_menu()

if __name__ == "__main__":
    app = POSApplication()
    app.run()
