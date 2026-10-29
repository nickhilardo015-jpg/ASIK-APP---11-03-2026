-- =====================================================================
--  schema.sql  --  MySQL database structure for the ASIK system
-- =====================================================================
--  HOW TO USE
--    Option A (recommended):  python setup_database.py
--        (it runs this file for you, then adds demo data)
--    Option B (manual):       mysql -u root -p < schema.sql
--
--  Every function of the app has its OWN table, as requested:
--    account_credentials ... usernames + hashed passwords (login)
--    user_roles ............ what each account is (job seeker, employer,
--                            lender, admin).  One account may hold many roles.
--    user_profiles ......... profile information + profile photo path
--    ph_locations .......... Region > Province > Municipality filter data
--    companies ............. farms / companies with a full address
--    employer_details ...... links an employer account to its company
--    job_vacancies ......... "Hiring Now!" job posts (salary in PHP)
--    job_applications ...... the job seeker CRUD form + hiring status
--    equipment ............. rentable equipment with location + price
--    equipment_rentals ..... reservations made by renters
--    messages .............. the messaging page
--    message_hidden ........ messages a user deleted "for me only"
--    chat_settings ......... each user's chat colour theme
--    farm_tasks ............ the farm schedule page
--    community_* ........... the Community page (11 tables, see section 13)
--    about_* ............... the About page content (3 tables, see section 14)
-- =====================================================================

-- Create the database if it does not exist yet, then select it.
CREATE DATABASE IF NOT EXISTS asik_database
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE asik_database;

-- ---------------------------------------------------------------------
-- 1. account_credentials : login information (NEVER stores plain passwords)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS account_credentials (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,   -- unique id of the account
    username       VARCHAR(50)  NOT NULL UNIQUE,     -- login name
    password_salt  VARCHAR(64)  NOT NULL,            -- random salt per user
    password_hash  VARCHAR(128) NOT NULL,            -- PBKDF2 hash (not the real password)
    is_active      TINYINT(1)   NOT NULL DEFAULT 1,  -- admin can disable an account (0)
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. user_roles : the role(s) of each account
--    'lender' = a person who lends/rents out equipment, 'renter' kept
--    inside the same table so a user can also rent from others.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_roles (
    role_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id  INT NOT NULL,
    role     ENUM('admin','job_seeker','employer','lender','renter') NOT NULL,
    UNIQUE KEY uq_user_role (user_id, role),         -- no duplicate roles
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. user_profiles : who the user is (shown on the Profile page)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id       INT PRIMARY KEY,                   -- 1 profile per account
    full_name     VARCHAR(120) NOT NULL,
    email         VARCHAR(120),
    phone         VARCHAR(30),
    region        VARCHAR(80),
    province      VARCHAR(80),
    municipality  VARCHAR(80),
    address       VARCHAR(255),                      -- street / barangay
    bio           TEXT,                              -- short "about me"
    photo_path    VARCHAR(255),                      -- path of uploaded profile photo
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. ph_locations : data behind the Region > Province > Municipality filters
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ph_locations (
    location_id   INT AUTO_INCREMENT PRIMARY KEY,
    region        VARCHAR(80) NOT NULL,
    province      VARCHAR(80) NOT NULL,
    municipality  VARCHAR(80) NOT NULL,
    INDEX idx_region (region),
    INDEX idx_province (province)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. companies : farms / companies that hire (mock + employer-created)
--    full_address is built automatically from the parts below.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    company_id    INT AUTO_INCREMENT PRIMARY KEY,
    company_name  VARCHAR(150) NOT NULL,
    owner_user_id INT NULL,                          -- NULL = demo/mock company
    street        VARCHAR(150),
    municipality  VARCHAR(80) NOT NULL,
    province      VARCHAR(80) NOT NULL,
    region        VARCHAR(80) NOT NULL,
    full_address  VARCHAR(400) NOT NULL,             -- "street, municipality, province, region"
    FOREIGN KEY (owner_user_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. employer_details : extra info for employer accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employer_details (
    user_id         INT PRIMARY KEY,
    company_id      INT NULL,                        -- the farm/company they manage
    position_title  VARCHAR(100),                    -- e.g. Owner, HR Manager
    business_permit VARCHAR(100),                    -- permit / registration no.
    contact_number  VARCHAR(30),
    FOREIGN KEY (user_id)    REFERENCES account_credentials(user_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 7. job_vacancies : the "Hiring Now!" listings (salary is per DAY in PHP)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_vacancies (
    vacancy_id      INT AUTO_INCREMENT PRIMARY KEY,
    company_id      INT NOT NULL,
    posted_by       INT NULL,                        -- employer user (NULL = demo data)
    job_title       VARCHAR(120) NOT NULL,
    job_level       ENUM('Expert','Skilled','Laborer') NOT NULL,
    description     TEXT NOT NULL,
    salary_per_day  DECIMAL(10,2) NOT NULL,          -- Philippine peso per day
    days_per_week   TINYINT NOT NULL,
    hours_per_week  TINYINT NOT NULL,
    slots           INT NOT NULL DEFAULT 1,          -- open positions
    status          ENUM('Open','Closed') NOT NULL DEFAULT 'Open',
    posted_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (posted_by)  REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 8. job_applications : filled in by job seekers (Create/Read/Update/Delete)
--    status changes to 'Hired' when the employer presses the Hire button.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id   INT NOT NULL,                     -- the job seeker's account
    vacancy_id     INT NOT NULL,                     -- job applied for
    company_id     INT NOT NULL,                     -- farm/company applied to
    full_name      VARCHAR(120) NOT NULL,
    age            TINYINT,
    contact_number VARCHAR(30) NOT NULL,
    email          VARCHAR(120),
    region         VARCHAR(80),
    province       VARCHAR(80),
    municipality   VARCHAR(80),
    address        VARCHAR(255),
    skills         VARCHAR(255),
    experience     TEXT,
    status         ENUM('Pending','Interview','Hired','Rejected') NOT NULL DEFAULT 'Pending',
    applied_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (applicant_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE,
    FOREIGN KEY (vacancy_id)   REFERENCES job_vacancies(vacancy_id)    ON DELETE CASCADE,
    FOREIGN KEY (company_id)   REFERENCES companies(company_id)        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. equipment : farm equipment / ICT tools available for rent
--    owner_user_id = the lender; NULL = listed by Asik itself.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id   INT AUTO_INCREMENT PRIMARY KEY,
    owner_user_id  INT NULL,
    name           VARCHAR(120) NOT NULL,
    icon           VARCHAR(10)  NOT NULL DEFAULT '🚜',
    category       ENUM('Heavy Equipment','ICT Farming Tools') NOT NULL,
    description    VARCHAR(255),
    price_per_day  DECIMAL(10,2) NOT NULL,           -- PHP per day
    region         VARCHAR(80) NOT NULL,
    province       VARCHAR(80) NOT NULL,
    municipality   VARCHAR(80) NOT NULL,
    is_available   TINYINT(1) NOT NULL DEFAULT 1,
    listed_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. equipment_rentals : reservations made on the Rental page
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment_rentals (
    rental_id     INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id  INT NOT NULL,
    renter_id     INT NOT NULL,
    days          INT NOT NULL,
    total_price   DECIMAL(12,2) NOT NULL,
    farm_location VARCHAR(255),                      -- where it will be used (their farm)
    status        ENUM('Reserved','Cancelled','Completed') NOT NULL DEFAULT 'Reserved',
    reserved_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE,
    FOREIGN KEY (renter_id)    REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11. messages : user-to-user chat
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    message_id   INT AUTO_INCREMENT PRIMARY KEY,
    sender_id    INT NOT NULL,
    receiver_id  INT NOT NULL,
    body         TEXT NOT NULL,
    sent_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read      TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (sender_id)   REFERENCES account_credentials(user_id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11b. message_hidden : "delete for me only"
--      One row = one message that ONE user has deleted from their own view.
--      The other person still sees the message (the row in `messages` stays).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS message_hidden (
    message_id   INT NOT NULL,
    user_id      INT NOT NULL,                       -- the user who hid it
    PRIMARY KEY (message_id, user_id),
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11c. chat_settings : each user's chat colour theme
--      my_color   = colour of my own message bubbles
--      chat_bg    = colour of the chat background
--      role_coded = 1: the other person's bubbles use their role colour
--                      (admin / employer / lender / renter / job seeker)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_settings (
    user_id     INT PRIMARY KEY,
    my_color    VARCHAR(7) NOT NULL DEFAULT '#DDF0DA',
    chat_bg     VARCHAR(7) NOT NULL DEFAULT '#FFFFFF',
    role_coded  TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 12. farm_tasks : the Farm Schedule page
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS farm_tasks (
    task_id    INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    title      VARCHAR(150) NOT NULL,
    task_date  DATE NOT NULL,
    task_time  VARCHAR(10),
    task_type  VARCHAR(40),
    is_done    TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 13. Community page (tips, techniques, entertainment and marketplace posts)
--     community_posts ....... the posts (category, title, description, optional photo)
--     community_reactions ... one thumbs up / thumbs down per user per post
--     community_comments .... comments (can be edited / removed by their writer)
--     community_saves ....... posts a user bookmarked
--     community_shares ...... posts a user shared on their profile
--     community_seen ........ when a user last opened their notifications
--     community_reports ..... reports users made about a post (moderation)
--     community_mod_log ..... every admin decision: take down, keep, uphold, put back (reason is optional)
--     community_appeals ..... an owner's appeal against a take-down, and the admin's decision
--     community_appeal_files  evidence files attached to an appeal
--     community_meta ........ remembers that the starter posts were added
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS community_posts (
    post_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    title       VARCHAR(150) NOT NULL,
    body        TEXT NOT NULL,
    photo_path  VARCHAR(255) NULL,
    price       VARCHAR(60)  NULL,
    location    VARCHAR(150) NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at   TIMESTAMP NULL DEFAULT NULL,
    is_removed  TINYINT(1) NOT NULL DEFAULT 0,          -- 1 = taken down by an admin (hidden, not deleted)
    removed_at  TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_post_category (category),
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_reactions (
    post_id     INT NOT NULL,
    user_id     INT NOT NULL,
    reaction    VARCHAR(4) NOT NULL,
    reacted_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_comments (
    comment_id  INT AUTO_INCREMENT PRIMARY KEY,
    post_id     INT NOT NULL,
    user_id     INT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at   TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_saves (
    post_id   INT NOT NULL,
    user_id   INT NOT NULL,
    saved_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_shares (
    post_id    INT NOT NULL,
    user_id    INT NOT NULL,
    shared_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_seen (
    user_id  INT PRIMARY KEY,
    seen_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_reports (
    report_id    INT AUTO_INCREMENT PRIMARY KEY,
    post_id      INT NOT NULL,
    reporter_id  INT NOT NULL,
    reason       VARCHAR(60)  NOT NULL,
    details      VARCHAR(255) NULL,
    status       VARCHAR(10)  NOT NULL DEFAULT 'Open',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_one_report (post_id, reporter_id),
    FOREIGN KEY (post_id)     REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (reporter_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_mod_log (
    log_id         INT AUTO_INCREMENT PRIMARY KEY,
    post_id        INT NULL,
    post_title     VARCHAR(150) NOT NULL,
    category       VARCHAR(30),
    owner_id       INT NULL,
    admin_id       INT NULL,
    action         VARCHAR(12) NOT NULL DEFAULT 'Take down',   -- Take down, Keep, Uphold or Restore
    reason         TEXT NULL,                                  -- the explanation is optional
    taken_down_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL,
    FOREIGN KEY (admin_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_appeals (
    appeal_id   INT AUTO_INCREMENT PRIMARY KEY,
    log_id      INT NULL,
    post_id     INT NOT NULL,
    user_id     INT NOT NULL,
    details     TEXT NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'Pending',    -- Pending, Upheld or Restored
    admin_id    INT NULL,
    admin_note  TEXT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at  TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_appeal_status (status),
    FOREIGN KEY (post_id)  REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES account_credentials(user_id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_appeal_files (
    file_id    INT AUTO_INCREMENT PRIMARY KEY,
    appeal_id  INT NOT NULL,
    file_path  VARCHAR(255) NOT NULL,
    FOREIGN KEY (appeal_id) REFERENCES community_appeals(appeal_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_meta (
    k  VARCHAR(40) PRIMARY KEY,
    v  VARCHAR(255)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 14. About page content (editable by an administrator)
--     about_settings ... headline, section titles, notices, announcement
--     about_items ...... the info cards and the community guidelines
--     about_team ....... the developers / team with their photos
--     about_suggestions  what users suggest: improvements and new features
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS about_settings (
    k           VARCHAR(40) PRIMARY KEY,             -- name of the text, e.g. hero_title
    v           TEXT,                                -- the wording itself
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS about_items (
    item_id     INT AUTO_INCREMENT PRIMARY KEY,
    kind        VARCHAR(20)  NOT NULL,               -- 'card' or 'guideline'
    icon        VARCHAR(10),
    title       VARCHAR(120) NOT NULL,
    body        TEXT NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    INDEX idx_about_kind (kind)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS about_team (
    member_id   INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    role        VARCHAR(120),
    bio         TEXT,
    photo_path  VARCHAR(255),
    sort_order  INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS about_suggestions (
    suggestion_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    improve        TEXT NULL,
    feature        TEXT NULL,
    status         VARCHAR(10) NOT NULL DEFAULT 'New',
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_suggestion_status (status),
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;
