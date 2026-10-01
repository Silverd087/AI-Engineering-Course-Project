-- Authors
INSERT INTO authors (id, name, country) VALUES
(1, 'Isabel Ortega', 'Spain'),
(2, 'Kenji Watanabe', 'Japan'),
(3, 'Amara Diallo', 'Senegal'),
(4, 'Lucas Bennett', 'UK'),
(5, 'Mei Lin', 'China'),
(6, 'Samuel Okafor', 'Nigeria'),
(7, 'Elena Novak', 'Poland'),
(8, 'Youssef Haddad', 'Tunisia');

-- Books
INSERT INTO books (id, title, author_id, genre, price, published_year, stock) VALUES
(1,  'The Glass Orchard',        1, 'Fiction',    14.99, 2018, 32),
(2,  'Salt and Shadow',          1, 'Fiction',    16.50, 2021, 14),
(3,  'Quiet Reactor',            2, 'Sci-Fi',     19.99, 2016, 9),
(4,  'Neon Monsoon',             2, 'Sci-Fi',     21.00, 2022, 27),
(5,  'The Baobab Letters',       3, 'Fiction',    12.75, 2015, 41),
(6,  'River of Names',           3, 'Poetry',     9.50,  2019, 18),
(7,  'Clockwork Harbor',         4, 'Mystery',    15.25, 2020, 23),
(8,  'The Last Ledger',          4, 'Mystery',    17.00, 2023, 6),
(9,  'Porcelain Winter',         5, 'Fiction',    13.40, 2017, 29),
(10, 'Silk Algorithms',          5, 'Sci-Fi',     22.50, 2024, 11),
(11, 'Harmattan Heart',         6, 'Fiction',    11.99, 2014, 37),
(12, 'The Copper Market',       6, 'Non-Fiction', 24.00, 2021, 15),
(13, 'Frostbound',               7, 'Fantasy',    18.75, 2019, 20),
(14, 'The Salt Cartographer',    7, 'Fantasy',    20.25, 2022, 8),
(15, 'Desert Static',            8, 'Sci-Fi',     16.80, 2020, 33),
(16, 'Minaret Blue',             8, 'Poetry',     8.99,  2016, 25),
(17, 'The Quiet Algorithm',      2, 'Non-Fiction', 26.50, 2023, 5),
(18, 'Bone China',               5, 'Mystery',    15.99, 2018, 19),
(19, 'The Ember Ledger',         4, 'Mystery',    17.50, 2024, 12),
(20, 'Low Tide Republic',        1, 'Non-Fiction', 23.00, 2020, 10);

-- Customers
INSERT INTO customers (id, name, email, country, signup_date) VALUES
(1,  'Hana Suzuki',      'hana.s@example.com',    'Japan',   '2021-03-14'),
(2,  'Diego Fernandez',  'diego.f@example.com',   'Spain',   '2020-07-02'),
(3,  'Grace Mensah',     'grace.m@example.com',   'Ghana',   '2022-01-19'),
(4,  'Oliver Smith',     'oliver.s@example.com',  'UK',      '2019-11-30'),
(5,  'Amina Haddad',     'amina.h@example.com',   'Tunisia', '2023-05-08'),
(6,  'Wei Zhang',        'wei.z@example.com',     'China',   '2021-09-23'),
(7,  'Chidi Eze',        'chidi.e@example.com',   'Nigeria', '2022-12-01'),
(8,  'Marta Kowalska',   'marta.k@example.com',   'Poland',  '2020-02-17'),
(9,  'Fatou Ndiaye',     'fatou.n@example.com',   'Senegal', '2023-08-25'),
(10, 'James Carter',     'james.c@example.com',   'UK',      '2018-06-10');

-- Orders
INSERT INTO orders (id, customer_id, order_date, status) VALUES
(1,  1,  '2023-01-10', 'shipped'),
(2,  2,  '2023-01-15', 'shipped'),
(3,  3,  '2023-02-02', 'cancelled'),
(4,  1,  '2023-02-20', 'shipped'),
(5,  4,  '2023-03-05', 'shipped'),
(6,  5,  '2023-03-18', 'placed'),
(7,  6,  '2023-04-01', 'shipped'),
(8,  7,  '2023-04-12', 'shipped'),
(9,  2,  '2023-05-09', 'cancelled'),
(10, 8,  '2023-05-22', 'shipped'),
(11, 9,  '2023-06-14', 'shipped'),
(12, 10, '2023-06-30', 'placed'),
(13, 3,  '2023-07-11', 'shipped'),
(14, 6,  '2023-08-02', 'shipped'),
(15, 1,  '2023-09-19', 'shipped');

-- Order items
INSERT INTO order_items (id, order_id, book_id, quantity, unit_price) VALUES
(1,  1,  1,  2, 14.99),
(2,  1,  6,  1, 9.50),
(3,  2,  3,  1, 19.99),
(4,  3,  4,  1, 21.00),
(5,  4,  5,  3, 12.75),
(6,  4,  16, 2, 8.99),
(7,  5,  7,  1, 15.25),
(8,  5,  13, 1, 18.75),
(9,  6,  10, 1, 22.50),
(10, 7,  2,  2, 16.50),
(11, 7,  9,  1, 13.40),
(12, 8,  11, 4, 11.99),
(13, 9,  14, 1, 20.25),
(14, 10, 8,  1, 17.00),
(15, 10, 19, 1, 17.50),
(16, 11, 12, 1, 24.00),
(17, 11, 20, 1, 23.00),
(18, 12, 15, 2, 16.80),
(19, 13, 1,  1, 14.99),
(20, 13, 6,  2, 9.50),
(21, 14, 17, 1, 26.50),
(22, 14, 3,  1, 19.99),
(23, 15, 18, 1, 15.99),
(24, 15, 4,  1, 21.00),
(25, 2,  5,  2, 12.75),
(26, 6,  7,  1, 15.25),
(27, 8,  9,  3, 13.40),
(28, 12, 2,  1, 16.50),
(29, 9,  11, 1, 11.99),
(30, 15, 10, 1, 22.50);
