# ASIK-APP---11-03-2026
Final Requirement for subjects: PF101, CC104, IT AGRI
# Asik – Smart Agriculture (Tkinter + MySQL)

## 1. Install
    pip install -r requirements.txt        # mysql-connector-python, pillow
Tkinter ships with Python (Linux: `sudo apt install python3-tk`).

## 2. Configure MySQL
Open `config.py` and put your MySQL user/password (DB_USER, DB_PASSWORD).

## 3. Create the database `asik_database` + demo data
    python setup_database.py            # add --reset to rebuild from scratch

## 4. Run
    python main.py

## Demo accounts (username / password)
| Account | Login |
| Administrator | admin / admin123 |
| Job seeker | seeker / seeker123 |
| Employer | employer / employer123 |
| Lender (rents out equipment) | lender / lender123 |
| Employer + Lender | both / both123 |

## Files (one per page)
login_page, 
register_page,
dashboard_page, 
rental_page, 
lender_page, 
jobs_page (Hiring Now!),
apply_page (job seeker CRUD), 
post_vacancy_page, 
applicants_page, 
messages_page, 
profile_page,
schedule_page, 
about_page, 
admin_page.  Shared: main, 
theme, database, 
session, 
config, 
ph_locations,
schema.sql, 
setup_database.py. 

# Logo: asik_logo.png.
