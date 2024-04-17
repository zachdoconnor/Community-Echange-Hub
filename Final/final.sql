-- User Table
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    f_name VARCHAR(255),
    l_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    user_password VARCHAR(255),
    profile_image VARCHAR(255),
    location VARCHAR(255),
    is_admin INTEGER DEFAULT 0,
    joinDate DEFAULT CURRENT_TIMESTAMP,
    lastLogin DATE
);

-- Listing Table
CREATE TABLE Listings (
    listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INT,
    title VARCHAR(255),
    description TEXT,
    images TEXT, -- assuming multiple image URLs stored as JSON or separated by some delimiter
    category VARCHAR(255),
    date_posted DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Message Table
CREATE TABLE Message (
    messageID INTEGER PRIMARY KEY AUTOINCREMENT,
    senderID INT,
    receiverID INT,
    listing_id INT, -- made optional by allowing NULL values
    content TEXT,
    sendDate DATETIME,
    isRead BOOLEAN,
    FOREIGN KEY (senderID) REFERENCES Users(user_id),
    FOREIGN KEY (receiverID) REFERENCES Users(user_id),
    FOREIGN KEY (listing_id) REFERENCES Listings(listing_id)
);

-- Review Table
CREATE TABLE Review (
    reviewID INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewerID INT,
    reviewedUserID INT,
    rating DECIMAL(2, 1), -- allows for a rating scale with one decimal place, e.g., 4.5
    comment TEXT,
    datePosted DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reviewerID) REFERENCES Users(user_id),
    FOREIGN KEY (reviewedUserID) REFERENCES Users(user_id)
);

-- Category Table
CREATE TABLE Category (
    categoryID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    description TEXT
);

INSERT INTO Category (categoryID, name, description) VALUES
(1, 'Electronics', 'Devices and gadgets related to electrical and electronic engineering'),
(2, 'Furniture', 'Items used to support various human activities such as seating and sleeping'),
(3, 'Clothing', 'Items worn on the body, typically made from fabrics or textiles'),
(4, 'Books', 'Collections of written, printed, illustrated, or blank sheets, made of ink, paper, parchment, or other materials'),
(5, 'Vehicles', 'Modes of transport that help people move from one place to another'),
(6, 'Sports Equipment', 'Items required to play sports or for physical exercise'),
(7, 'Home Appliances', 'Electrical/mechanical machines that accomplish some household functions'),
(8, 'Garden', 'Tools and accessories related to the practice of gardening'),
(9, 'Toys', 'Items designed to be played with by children'),
(10, 'Art', 'Creative items and expressions in physical or digital form'),
(11, 'Music Instruments', 'Tools used to produce music'),
(12, 'Computers', 'Electronic devices capable of processing, storing, and retrieving data'),
(13, 'Mobile Phones', 'Portable telecommunication devices'),
(14, 'Services', 'Non-tangible commodities such as accountancy, banking, cleaning, consultancy, education, insurance, expertise, medical treatment, or transportation');

