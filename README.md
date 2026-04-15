# 🍕 Pizzeria App

A full-stack web application for managing and ordering food online, inspired by platforms like JustEat and Uber Eats.

This project includes a dynamic frontend, a FastAPI backend, and Stripe integration for payments.

---

## 🚀 Features

### 🧾 Customer Side

* Browse products by category (Pizza, Burgers, Drinks, etc.)
* Dynamic category navigation (scroll-based)
* Product descriptions and ingredients display
* Add items to cart
* Guest checkout (no account required)
* Stripe Checkout integration

### 🛠️ Admin Panel

* Create products (name, price, category, description, ingredients)
* Edit products from modal popup
* Delete products
* Manage order lifecycle (`created -> paid -> accepted -> printing -> printed -> ready -> delivered`)
* Trigger manual reprint for failed/missed tickets
* Real-time product updates
* Clean and responsive UI

### 🎨 UI / UX

* Dark / Light mode toggle
* Responsive design (mobile-friendly)
* Smooth animations and hover effects
* Category navigation similar to food delivery apps

---

## 🏗️ Tech Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* SQLite
* Stripe API

### Frontend

* HTML
* Tailwind CSS
* Vanilla JavaScript

---

## 📂 Project Structure

```
pizzeria-app/
│
├── app/
│   ├── main.py
│   ├── database/
│   ├── routers/
│   └── schemas/
│
├── frontend/
│   ├── index.html
│   └── admin.html
│
├── .env
├── .gitignore
└── pizzeria.db
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```
git clone https://github.com/AjdenizMartin/AppPizzeria.git
cd AppPizzeria
```

---

### 2. Create virtual environment

```
python -m venv .venv
source .venv/bin/activate
```

---

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

### 4. Configure environment variables

Create a `.env` file:

```
STRIPE_KEY=your_stripe_secret_key
SECRET_KEY=your_jwt_secret
ADMIN_EMAILS=owner@example.com
PRINT_AGENT_KEY=shared_secret_for_printer_agent
PRINT_JOB_MAX_ATTEMPTS=3
```

---

### 5. Run backend

```
python -m uvicorn app.main:app --reload
```

---

### 6. Run frontend

```
cd frontend
python3 -m http.server 5500
```

Open in browser:

```
http://127.0.0.1:5500
```

---

### 7. Run print agent (restaurant PC/tablet)

```
PRINT_AGENT_KEY=shared_secret_for_printer_agent python print_agent/agent.py --agent-id kitchen-tablet-1
```

Optional file sink (for testing without a physical printer):

```
PRINT_AGENT_KEY=shared_secret_for_printer_agent python print_agent/agent.py --output-file /tmp/print_tickets.txt
```

---

### 8. Auto-start print agent on Linux (systemd)

Make scripts executable and install service:

```
chmod +x ops/systemd/install_print_agent_service.sh
./ops/systemd/install_print_agent_service.sh /opt/pizzeria-app restaurant
```

Configure runtime secrets:

```
sudo nano /etc/pizzeria-print-agent.env
```

Restart and monitor:

```
sudo systemctl restart pizzeria-print-agent.service
sudo journalctl -u pizzeria-print-agent.service -f
```

Detailed guide: `ops/systemd/README.md`

---

## 💳 Stripe Testing

Use Stripe test cards:

```
4242 4242 4242 4242
Any future date
Any CVC
```

---

## 🔐 Security Notes

* Stripe keys are stored in `.env` (not committed)
* `.gitignore` prevents sensitive data from being uploaded

---

## 🚀 Future Improvements

* Product images upload
* Advanced pizza builder (sizes + toppings)
* User authentication system
* Order history and tracking
* Admin dashboard improvements
* Deployment (Docker / Cloud)

---

## 📸 Preview

(Add screenshots here)

---

## 👨‍💻 Author

**Angel Deniz**

* GitHub: https://github.com/AjdenizMartin

---

## ⭐️ Support

If you like this project, feel free to give it a star ⭐️
