# InvoiceAI / StockFlow

InvoiceAI / StockFlow is a Python and Streamlit application built to help small businesses process invoices, track stock, and export useful business data.

The project started from a real family business need: making invoice and inventory management easier for my mum. It began as a portfolio project, but the goal is to build something practical, simple and useful for small business stock control.

## Live Demo

Streamlit app:
https://invoiceai-krfykjsda24swyptqjal2d.streamlit.app/

## Project Purpose

Many small businesses still manage invoices, product quantities and stock manually. This can make it easy to lose track of:

* what was bought
* what was sold
* how much stock is currently available
* whether a product is running low
* whether a sale would make stock go negative

InvoiceAI / StockFlow aims to make this easier by combining invoice processing, manual invoice entry, inventory tracking, basic financial summaries and Excel exports in one simple app.

## Key Features

### Invoice Entry

The app supports two ways of adding invoices:

* PDF invoice upload
* Manual invoice entry

The manual invoice entry screen is simplified for non-technical users and focuses on the most important fields:

* product code
* product name
* quantity
* unit
* unit price
* line total

This makes it easier for a small business owner to enter invoices without being overwhelmed by technical fields.

### Inventory Tracking

Purchase invoices increase stock.

Sale invoices decrease stock.

The inventory dashboard shows:

* products being tracked
* current stock quantity
* low-stock items
* overall stock summary

### Negative Stock Protection

The app blocks sale invoices if there is not enough stock available.

Example:

* current stock: 3
* sale invoice quantity: 5
* result: invoice is not saved

This helps prevent accidental stock errors.

### Financial Dashboard

The financial dashboard gives a simple MVP-level view of:

* sales income
* purchase costs
* net result
* cash impact
* monthly summaries
* yearly summaries

This is not full accounting software, but it gives a useful business overview.

### Invoice History

Saved invoices can be reviewed in the invoice history section.

The app also allows invoice type correction if an invoice was accidentally saved as the wrong type.

### Manual Stock Adjustments

Manual stock adjustments can be used when stock needs correcting outside normal invoices, for example:

* damaged items
* missing stock
* stock count corrections
* stock added without an invoice

### Excel Exports

The app can export business data to Excel, including:

* full Excel report
* inventory report
* invoice history
* financial summary
* manual adjustments

This gives the user an extra safety copy outside the app.

### Database Backups

The app includes database backup functionality.

Backups can be created manually, and the app also creates safety backups before important database changes.

### Polish and English Interface

The app includes a bilingual interface:

* Polish
* English

This makes the project more practical for real use in a family/small business setting.

## Tech Stack

* Python
* Streamlit
* SQLite
* Pandas
* OpenPyXL
* Git and GitHub

## Project Structure

```text
InvoiceAI/
│
├── app.py              # Main Streamlit application
├── database.py         # Database, inventory and stock validation logic
├── extractor.py        # Invoice field and line item extraction logic
├── ocr.py              # PDF text extraction logic
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
│
├── data/               # Local SQLite database folder
├── backups/            # Local database backups
└── invoices/           # Uploaded invoice files
```

## How to Run Locally

Clone the repository:

```bash
git clone https://github.com/karacagaymonika/InvoiceAI.git
```

Go into the project folder:

```bash
cd InvoiceAI
```

Create and activate a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Important Note

This is currently a demo/MVP project.

The app is suitable for:

* portfolio demonstration
* testing
* small business workflow exploration
* learning Python, Streamlit, data handling and automation

Before using it as a real daily business system, the database should be moved from local SQLite to a proper online database such as Supabase/PostgreSQL.

## Future Improvements

Planned improvements include:

* product categories
* low-stock thresholds by product/category
* improved product master list
* user login
* online PostgreSQL/Supabase database
* improved PDF invoice extraction
* better reporting dashboard
* product-level profit calculations
* VAT handling
* sales and purchase trend charts

## What I Learned

Through this project, I practised:

* building a real Streamlit application
* using SQLite for structured data storage
* creating inventory logic
* preventing negative stock
* exporting data to Excel
* building bilingual UI text
* using Git branches for feature development
* improving a project step by step based on real user needs

## Project Status

Current status: active MVP development.

The app currently supports invoice entry, inventory tracking, negative stock protection, Excel exports, database backups and bilingual Polish/English use.
