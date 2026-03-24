import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="kensley.2005.nj@gmail.com",
    password="Hollowv2005!",        # add your MySQL password here
    database="sharknet"
)
cursor = conn.cursor()

# USERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS USERS (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    nsu_email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL
)
""")

# USER_PROFILES
cursor.execute("""
CREATE TABLE IF NOT EXISTS USER_PROFILES (
    profile_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    major VARCHAR(150) NULL,
    graduation_year YEAR NULL,
    bio TEXT NULL,
    profile_picture_url VARCHAR(500) NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
)
""")

# DEPARTMENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS DEPARTMENTS (
    department_id INT PRIMARY KEY AUTO_INCREMENT,
    department_name VARCHAR(100) NOT NULL,
    department_code VARCHAR(10) NOT NULL
)
""")

# SUBJECTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS SUBJECTS (
    subject_id INT PRIMARY KEY AUTO_INCREMENT,
    department_id INT NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    FOREIGN KEY (department_id) REFERENCES DEPARTMENTS(department_id)
)
""")

# COURSES
cursor.execute("""
CREATE TABLE IF NOT EXISTS COURSES (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    subject_id INT NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    course_number VARCHAR(20) NOT NULL,
    professor VARCHAR(150) NULL,
    semester VARCHAR(20) NULL,
    FOREIGN KEY (subject_id) REFERENCES SUBJECTS(subject_id)
)
""")

# HOMEWORK_POSTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS HOMEWORK_POSTS (
    post_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    category ENUM('homework', 'exam', 'professor', 'resource', 'general') NOT NULL DEFAULT 'general',
    view_count INT NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id),
    FOREIGN KEY (course_id) REFERENCES COURSES(course_id)
)
""")

# TUTOR_POSTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS TUTOR_POSTS (
    tutor_post_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    availability VARCHAR(300) NULL,
    contact_info VARCHAR(300) NULL,
    hourly_rate DECIMAL(6,2) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id),
    FOREIGN KEY (course_id) REFERENCES COURSES(course_id)
)
""")

# COMMENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS COMMENTS (
    comment_id INT PRIMARY KEY AUTO_INCREMENT,
    homework_post_id INT NOT NULL,
    user_id INT NOT NULL,
    body TEXT NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (homework_post_id) REFERENCES HOMEWORK_POSTS(post_id),
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
)
""")

# VOTES
cursor.execute("""
CREATE TABLE IF NOT EXISTS VOTES (
    vote_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    target_type ENUM('homework_post', 'comment') NOT NULL,
    target_id INT NOT NULL,
    vote_value TINYINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_vote (user_id, target_type, target_id),
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
)
""")

# BOOKMARKS
cursor.execute("""
CREATE TABLE IF NOT EXISTS BOOKMARKS (
    bookmark_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    target_type ENUM('homework_post', 'tutor_post') NOT NULL,
    target_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_bookmark (user_id, target_type, target_id),
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
)
""")

# TUTOR_REVIEWS
cursor.execute("""
CREATE TABLE IF NOT EXISTS TUTOR_REVIEWS (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    tutor_post_id INT NOT NULL,
    reviewer_user_id INT NOT NULL,
    rating TINYINT NOT NULL,
    review_text TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tutor_post_id) REFERENCES TUTOR_POSTS(tutor_post_id),
    FOREIGN KEY (reviewer_user_id) REFERENCES USERS(user_id)
)
""")

# TAGS
cursor.execute("""
CREATE TABLE IF NOT EXISTS TAGS (
    tag_id INT PRIMARY KEY AUTO_INCREMENT,
    tag_name VARCHAR(80) NOT NULL UNIQUE
)
""")

# POST_TAGS
cursor.execute("""
CREATE TABLE IF NOT EXISTS POST_TAGS (
    post_tag_id INT PRIMARY KEY AUTO_INCREMENT,
    post_type ENUM('homework_post', 'tutor_post') NOT NULL,
    post_id INT NOT NULL,
    tag_id INT NOT NULL,
    UNIQUE KEY unique_post_tag (post_type, post_id, tag_id),
    FOREIGN KEY (tag_id) REFERENCES TAGS(tag_id)
)
""")

conn.commit()
conn.close()
print("SharkNet database ready!")
