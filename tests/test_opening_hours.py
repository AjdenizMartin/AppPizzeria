from datetime import datetime

from app.database import models
from app.services.restaurant_service import is_restaurant_open


def _payload(product_id: int):
    return {
        'items': [{'product_id': product_id, 'quantity': 1, 'extras': ''}],
        'customer_name': 'Ana Client',
        'customer_email': 'ana@example.com',
        'customer_phone': '123456',
        'delivery_address': 'Main St',
        'delivery_city': 'Athlone',
        'delivery_postal_code': 'N37',
        'delivery_notes': '',
        'payment_method': 'card',
    }


def test_status_endpoint_returns_open_closed(client):
    response = client.get('/restaurant/status')
    assert response.status_code == 200
    data = response.json()
    assert 'is_open' in data and 'message' in data


def test_admin_can_update_opening_hours(client, admin_auth_headers):
    payload = [
        {'day_of_week': d, 'opens_at': '10:00', 'closes_at': '22:00', 'is_closed': False}
        for d in range(7)
    ]
    put = client.put('/admin/restaurant/opening-hours', json=payload, headers=admin_auth_headers)
    assert put.status_code == 200
    assert len(put.json()) == 7


def test_non_admin_cannot_update_opening_hours(client):
    payload = [{'day_of_week': 0, 'opens_at': '10:00', 'closes_at': '22:00', 'is_closed': False}]
    response = client.put('/admin/restaurant/opening-hours', json=payload)
    assert response.status_code == 401


def test_temporary_closed_blocks_orders(client, db_session, admin_auth_headers):
    client.patch(
        '/admin/restaurant/temporary-closure',
        json={'temporary_closed': True, 'temporary_closed_message': 'Closed now'},
        headers=admin_auth_headers,
    )
    product = models.Product(name='Pizza', price=10.0, category='Pizzas', description='X')
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post('/orders', json=_payload(product.id))
    assert response.status_code == 400
    assert 'closed' in response.json()['detail'].lower()


def test_order_allowed_in_opening_window(client, db_session, admin_auth_headers):
    client.patch(
        '/admin/restaurant/temporary-closure',
        json={'temporary_closed': False, 'temporary_closed_message': ''},
        headers=admin_auth_headers,
    )
    client.put(
        '/admin/restaurant/opening-hours',
        json=[
            {'day_of_week': d, 'opens_at': '00:00', 'closes_at': '23:59', 'is_closed': False}
            for d in range(7)
        ],
        headers=admin_auth_headers,
    )
    product = models.Product(name='Pizza', price=10.0, category='Pizzas', description='X')
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post('/orders', json=_payload(product.id))
    assert response.status_code == 201


def test_service_closed_outside_window(db_session):
    settings = models.RestaurantSettings(id=1, restaurant_name='Pizzeria')
    db_session.merge(settings)
    db_session.commit()
    db_session.add(
        models.OpeningHour(
            day_of_week=0,
            opens_at='10:00',
            closes_at='11:00',
            is_closed=False,
        )
    )
    db_session.commit()
    result = is_restaurant_open(db_session, now=datetime(2026, 5, 4, 12, 0))
    assert result['is_open'] is False
