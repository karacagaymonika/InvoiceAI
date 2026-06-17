# InvoiceAI / StockFlow

**InvoiceAI / StockFlow** is a bilingual invoice processing and inventory management application built with Python and Streamlit.

The project started as a portfolio showcase for invoice automation, but it grew into a practical stock management tool inspired by a real small-business problem: keeping track of products bought and sold through invoices.

The app allows users to upload invoice PDFs, extract invoice and product information, classify invoices as purchases or sales, and automatically update inventory levels.

---

## Features

### Invoice Processing

* Upload invoice PDF files
* Extract invoice information from text
* Extract product line items
* Store invoices in a local database
* View invoice history
* Delete invoices when needed

### Inventory Management

* Purchase invoices increase stock levels
* Sale invoices decrease stock levels
* Inventory dashboard showing product quantities
* Manual stock adjustments
* Delete manual stock adjustments
* Stock movement tracking

### Financial Dashboard

* View financial summaries
* Monthly summaries
* Yearly summaries
* Track invoice values by type

### Bilingual Interface

* English interface
* Polish interface
* Easy language selection inside the app

---

## Why I Built This Project

I built this project because I wanted to create something practical, not only something that looks good in a portfolio.

The original idea was simple invoice processing. After discussing it with my mum, I realised that small businesses often need more than just invoice storage. They also need a way to understand stock movement, especially when products are bought and sold through invoices.

That is why I expanded the project into a combined invoice processing and inventory management tool.

This project helped me practise:

* Python programming
* Streamlit app development
* Working with databases
* OCR and text extraction
* Data cleaning and structuring
* Inventory logic
* Financial summaries
* Building a user-friendly interface
* Creating bilingual software

---

## Tech Stack

* Python
* Streamlit
* SQLite
* Pandas
* PDF text extraction
* OCR support
* Git and GitHub

---

## Project Structure

```text
InvoiceAI/
│
├── app.py              # Main Streamlit application
├── database.py         # Database functions and stock logic
├── extractor.py        # Invoice and product extraction logic
├── ocr.py              # PDF text extraction / OCR logic
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
├── .gitignore          # Files excluded from Git
│
├── invoices/           # Uploaded invoice files, ignored by Git
└── venv/               # Virtual environment, ignored by Git
```

---

## How the App Works

1. The user uploads an invoice PDF.
2. The app extracts invoice text from the PDF.
3. Invoice fields and product line items are detected.
4. The user selects whether the invoice is a purchase invoice or a sale invoice.
5. The invoice is saved into the database.
6. Stock levels are updated automatically:

   * purchase invoice = stock increases
   * sale invoice = stock decreases
7. The user can view dashboards, history, summaries, and inventory movement.

---

## Example Use Cases

This project could be useful for:

* Small shops
* Family businesses
* Sole traders
* Inventory-based businesses
* Portfolio demonstration for automation and data roles
* Document processing and workflow automation examples

---

## Current Status

The app is currently working and includes:

* Invoice upload
* Product extraction
* Purchase invoice stock increase
* Sale invoice stock deduction
* Inventory dashboard
* Financial dashboard
* Monthly summaries
* Yearly summaries
* Invoice history
* Delete invoice function
* Manual stock adjustments
* Delete manual adjustments
* Polish / English interface

---

## Future Improvements

Planned future improvements include:

* Improved invoice field extraction accuracy
* Better support for different invoice layouts
* Export inventory and financial reports to Excel
* User login system
* Cloud database option
* Supplier and customer management
* Low-stock alerts
* Better product matching
* More advanced analytics dashboard
* Deployment online

---

## Screenshots

Screenshots will be added later as the project interface becomes more polished.

Planned screenshots:

* Upload invoice page
* Inventory dashboard
* Financial dashboard
* Invoice history
* Polish interface

---

## How to Run the Project Locally

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_LINK
```

### 2. Open the project folder

```bash
cd InvoiceAI
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

On Windows:

```bash
venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the Streamlit app

```bash
streamlit run app.py
```

---

## Important Note

This project is for learning, portfolio development, and demonstration purposes.

It currently uses test or example invoice data only. It should not be used for real financial, legal, tax, or accounting decisions without further validation and professional review.

---

## What I Learned

While building this project, I learned how to turn a real-life business problem into a working software tool.

I improved my understanding of:

* Python application structure
* Streamlit layouts and dashboards
* Database design using SQLite
* Inventory calculations
* Invoice data extraction
* Git version control
* Debugging and improving code step by step
* Building a project that solves a real problem

---

## Author

**Monika Sandra Karacagay**

Aspiring AI & Data Science professional with a background in document control, process management, and business administration.

I am building practical automation and data projects to solve real business problems and develop my portfolio.
