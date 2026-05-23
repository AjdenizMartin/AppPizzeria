from app.database import models


def test_public_settings_endpoint(client):
    response = client.get('/restaurant/settings')
    assert response.status_code == 200
    data = response.json()
    assert 'restaurant_name' in data
    assert 'delivery_fee' in data
    assert 'address' not in data


def test_admin_settings_requires_admin(client):
    response = client.get('/admin/restaurant/settings')
    assert response.status_code == 401


def test_admin_can_update_settings(client, admin_auth_headers):
    payload = {
        'restaurant_name': 'Pizzeria Roma',
        'public_phone': '123',
        'whatsapp_number': '456',
        'address': 'Main St',
        'delivery_fee': 3.0,
        'minimum_order_amount': 20.0,
        'estimated_delivery_minutes': 40,
        'is_accepting_orders': True,
        'banner_text': 'Open now',
    }
    response = client.patch('/admin/restaurant/settings', json=payload, headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.json()['restaurant_name'] == 'Pizzeria Roma'


def test_backend_uses_settings_delivery_fee_and_minimum(client, db_session, admin_auth_headers):
    client.patch(
        '/admin/restaurant/settings',
        json={
            'restaurant_name': 'Pizzeria',
            'public_phone': '',
            'whatsapp_number': '',
            'address': '',
            'delivery_fee': 5.0,
            'minimum_order_amount': 50.0,
            'estimated_delivery_minutes': 35,
            'is_accepting_orders': True,
            'banner_text': '',
        },
        headers=admin_auth_headers,
    )
    product = models.Product(name='Pizza', price=10.0, category='Pizzas', description='X')
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    low = client.post('/orders', json={
        'items': [{'product_id': product.id, 'quantity': 1, 'extras': ''}],
        'customer_name': 'Ana',
        'customer_email': 'a@a.com',
        'customer_phone': '111',
        'delivery_address': 'Addr',
        'delivery_city': 'City',
        'delivery_postal_code': 'Code',
        'delivery_notes': '',
        'payment_method': 'card',
    })
    assert low.status_code == 400


def test_orders_blocked_when_not_accepting(client, db_session, admin_auth_headers):
    client.patch(
        '/admin/restaurant/settings',
        json={
            'restaurant_name': 'Pizzeria',
            'public_phone': '',
            'whatsapp_number': '',
            'address': '',
            'delivery_fee': 2.5,
            'minimum_order_amount': 0.0,
            'estimated_delivery_minutes': 35,
            'is_accepting_orders': False,
            'banner_text': 'Closed',
        },
        headers=admin_auth_headers,
    )
    product = models.Product(name='Pizza', price=10.0, category='Pizzas', description='X')
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post('/orders', json={
        'items': [{'product_id': product.id, 'quantity': 1, 'extras': ''}],
        'customer_name': 'Ana',
        'customer_email': 'ana@example.com',
        'customer_phone': '111',
        'delivery_address': 'Addr',
        'delivery_city': 'City',
        'delivery_postal_code': 'Code',
        'delivery_notes': '',
        'payment_method': 'card',
    })
    assert response.status_code == 400
