# api.py - Pure Flask API Backend
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# In-memory data store (replace with database in production)
app_data = {
    'servers': [],
    'current_server_index': 0
}

class Table:
    def __init__(self, seats, table_number):
        self.seats = seats
        self.occupied = 0
        self.table_number = table_number
        self.last_seated = None

    def is_available(self):
        return self.occupied < self.seats

    def get_available_seats(self):
        return self.seats - self.occupied

    def occupy_seats(self, n):
        if self.get_available_seats() >= n:
            self.occupied += n
            self.last_seated = datetime.now().isoformat()
            return True
        return False

    def clear_table(self):
        self.occupied = 0
        self.last_seated = None

    def get_occupancy_rate(self):
        return round((self.occupied / self.seats) * 100, 1)

    def to_dict(self):
        return {
            'seats': self.seats,
            'occupied': self.occupied,
            'table_number': self.table_number,
            'last_seated': self.last_seated,
            'is_available': self.is_available(),
            'available_seats': self.get_available_seats(),
            'occupancy_rate': self.get_occupancy_rate()
        }

class Server:
    def __init__(self, name, table_seats):
        self.name = name
        self.tables = [Table(seats, i + 1) for i, seats in enumerate(table_seats)]
        self.total_seated_ever = 0
        self.total_tips = 0.0

    def get_current_guests(self):
        return sum(table.occupied for table in self.tables)

    def get_total_capacity(self):
        return sum(table.seats for table in self.tables)

    def has_table_for(self, n):
        return any(table.get_available_seats() >= n for table in self.tables)

    def seat_guests(self, n):
        available_tables = [t for t in self.tables if t.get_available_seats() >= n]
        if not available_tables:
            return False
        
        best_table = min(available_tables, key=lambda t: t.get_available_seats())
        
        if best_table.occupy_seats(n):
            self.total_seated_ever += n
            return best_table.table_number
        return False

    def clear_table(self, table_number):
        for table in self.tables:
            if table.table_number == table_number and table.occupied > 0:
                table.clear_table()
                return True
        return False

    def add_tip(self, amount):
        self.total_tips += amount

    def get_availability_percentage(self):
        total_capacity = self.get_total_capacity()
        current_guests = self.get_current_guests()
        return round(((total_capacity - current_guests) / total_capacity) * 100, 1)

    def reset_all(self):
        for table in self.tables:
            table.clear_table()
        self.total_seated_ever = 0
        self.total_tips = 0.0

    def to_dict(self):
        return {
            'name': self.name,
            'tables': [table.to_dict() for table in self.tables],
            'current_guests': self.get_current_guests(),
            'total_seated_ever': self.total_seated_ever,
            'total_tips': self.total_tips,
            'total_capacity': self.get_total_capacity(),
            'availability_percentage': self.get_availability_percentage()
        }

def initialize_servers():
    return [
        Server('John', [4, 2, 6]),
        Server('Jane', [3, 2, 4]),
        Server('Jack', [5, 2, 4]),
        Server('Jill', [4, 2, 4])
    ]

def get_servers():
    if not app_data['servers']:
        servers = initialize_servers()
        app_data['servers'] = [server.to_dict() for server in servers]
    
    # Reconstruct server objects
    servers = []
    for server_data in app_data['servers']:
        server = Server(server_data['name'], [])
        server.total_seated_ever = server_data['total_seated_ever']
        server.total_tips = server_data['total_tips']
        
        server.tables = []
        for table_data in server_data['tables']:
            table = Table(table_data['seats'], table_data['table_number'])
            table.occupied = table_data['occupied']
            table.last_seated = table_data['last_seated']
            server.tables.append(table)
        
        servers.append(server)
    
    return servers

def save_servers(servers):
    app_data['servers'] = [server.to_dict() for server in servers]

# API Routes
@app.route('/api/servers', methods=['GET'])
def get_servers_api():
    servers = get_servers()
    return jsonify({'servers': [server.to_dict() for server in servers]})

@app.route('/api/seat_party', methods=['POST'])
def seat_party():
    data = request.json
    party_size = int(data.get('party_size', 0))
    server_preference = data.get('server_preference', '')
    
    if party_size < 1 or party_size > 12:
        return jsonify({'success': False, 'message': 'Invalid party size. Please enter 1-12.'})
    
    servers = get_servers()
    current_server_index = app_data.get('current_server_index', 0)
    
    table_seated = False
    seated_server = None
    table_number = None
    
    # Try preferred server first
    if server_preference:
        preferred_server = next((s for s in servers if s.name == server_preference), None)
        if preferred_server and preferred_server.has_table_for(party_size):
            table_number = preferred_server.seat_guests(party_size)
            if table_number:
                table_seated = True
                seated_server = preferred_server
    
    # Use balanced distribution if no preference or preferred unavailable
    if not table_seated:
        available_servers = [s for s in servers if s.has_table_for(party_size)]
        
        if available_servers:
            available_servers.sort(key=lambda s: s.get_current_guests())
            min_guests = available_servers[0].get_current_guests()
            balanced_servers = [s for s in available_servers if s.get_current_guests() == min_guests]
            
            if len(balanced_servers) > 1:
                for _ in range(len(servers)):
                    candidate_server = servers[current_server_index]
                    current_server_index = (current_server_index + 1) % len(servers)
                    
                    if candidate_server in balanced_servers:
                        table_number = candidate_server.seat_guests(party_size)
                        if table_number:
                            table_seated = True
                            seated_server = candidate_server
                            break
            else:
                table_number = balanced_servers[0].seat_guests(party_size)
                if table_number:
                    table_seated = True
                    seated_server = balanced_servers[0]
        
        app_data['current_server_index'] = current_server_index
    
    if table_seated:
        save_servers(servers)
        return jsonify({
            'success': True,
            'message': f'Party of {party_size} seated at {seated_server.name}\'s Table {table_number}',
            'servers': [server.to_dict() for server in servers]
        })
    else:
        return jsonify({
            'success': False,
            'message': f'No table available for party of {party_size}. Please try a smaller party size.'
        })

@app.route('/api/clear_table', methods=['POST'])
def clear_table():
    data = request.json
    server_name = data.get('server_name')
    table_number = int(data.get('table_number'))
    
    servers = get_servers()
    server = next((s for s in servers if s.name == server_name), None)
    
    if server and server.clear_table(table_number):
        save_servers(servers)
        return jsonify({
            'success': True,
            'message': f'Table {table_number} cleared',
            'servers': [server.to_dict() for server in servers]
        })
    
    return jsonify({'success': False, 'message': 'Table not found or already empty'})

@app.route('/api/add_tip', methods=['POST'])
def add_tip():
    data = request.json
    server_name = data.get('server_name')
    tip_amount = float(data.get('tip_amount', 0))
    
    if tip_amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid tip amount'})
    
    servers = get_servers()
    server = next((s for s in servers if s.name == server_name), None)
    
    if server:
        server.add_tip(tip_amount)
        save_servers(servers)
        return jsonify({
            'success': True,
            'message': f'${tip_amount:.2f} tip added to {server_name}',
            'servers': [server.to_dict() for server in servers]
        })
    
    return jsonify({'success': False, 'message': 'Server not found'})

@app.route('/api/reset_all', methods=['POST'])
def reset_all():
    servers = get_servers()
    for server in servers:
        server.reset_all()
    
    save_servers(servers)
    app_data['current_server_index'] = 0
    
    return jsonify({
        'success': True,
        'message': 'All tables and statistics reset',
        'servers': [server.to_dict() for server in servers]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)